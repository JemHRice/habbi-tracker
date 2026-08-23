// Habbi-Tracker production infrastructure.
//
// Three resources: a Container Apps environment (a shared stage that can host
// future containerised projects at no extra cost), the API container app
// itself, and the Static Web App that serves the PWA.
//
// The whole thing is designed to sit inside free grants: the container app
// scales to zero when nobody is using it, and Static Web Apps' Free tier
// includes hosting, TLS and per-pull-request previews.

@description('Location for the Container Apps environment and API.')
param location string = resourceGroup().location

@description('Location for the Static Web App. Its Free tier is only offered in a few regions.')
@allowed([
  'centralus'
  'eastus2'
  'eastasia'
  'westeurope'
  'westus2'
])
param staticWebAppLocation string = 'eastasia'

@description('Prefix for resource names. Lowercase letters and digits.')
@minLength(3)
@maxLength(16)
param namePrefix string = 'habbitracker'

@description('Full image reference, e.g. ghcr.io/owner/habbi-tracker-api:sha.')
param apiImage string

@description('Postgres connection string for Neon. Stored as a Container Apps secret.')
@secure()
param databaseUrl string

@description('Comma-separated CORS origins the API accepts.')
param corsOrigins string = ''

@description('Regex matching Static Web Apps pull-request preview origins.')
param corsOriginRegex string = ''

@description('Exact number of digits a PIN must have.')
param pinLength int = 6

var environmentName = '${namePrefix}-env'
var apiName = '${namePrefix}-api'
var staticWebAppName = '${namePrefix}-web'
var logAnalyticsName = '${namePrefix}-logs'

// Container Apps requires a Log Analytics workspace for its console/system
// logs. The 30-day retention below stays inside the free ingestion grant at
// this scale.
resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: apiName
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        // Public HTTPS. Azure terminates TLS and the platform redirects HTTP.
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'database-url'
          value: databaseUrl
        }
      ]
      // No registry block: the image is a public GHCR package, so no pull
      // credential is needed. Making it private would require one here.
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'DATABASE_URL'
              secretRef: 'database-url'
            }
            {
              name: 'CORS_ORIGINS'
              value: corsOrigins
            }
            {
              name: 'CORS_ORIGIN_REGEX'
              value: corsOriginRegex
            }
            {
              name: 'PIN_LENGTH'
              value: string(pinLength)
            }
          ]
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 3
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        // Zero when idle — this is what makes the backend effectively free.
        // The cost is a cold start of a second or two on the first request of
        // the day, which for a habit tracker nobody will notice.
        minReplicas: 0
        maxReplicas: 1
        rules: [
          {
            name: 'http'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
}

resource web 'Microsoft.Web/staticSites@2023-12-01' = {
  name: staticWebAppName
  location: staticWebAppLocation
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    // The GitHub Actions workflow in this repo pushes builds, so Azure should
    // not also try to generate and commit one of its own.
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    provider: 'Custom'
  }
}

output apiUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
output apiName string = api.name
output staticWebAppName string = web.name
output staticWebAppUrl string = 'https://${web.properties.defaultHostname}'
output staticWebAppHostname string = web.properties.defaultHostname
