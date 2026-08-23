/**
 * Habbi, the app's bunny. She/her.
 *
 * Original artwork, drawn from scratch as plain SVG primitives: an olive
 * outline with blush fills in her ears and cheeks, and a small flower tucked at
 * the base of her left ear. Nothing here is traced from, or modelled on, any
 * existing character — the geometry is a handful of ellipses and stroked paths,
 * and the whole thing is defined in this file.
 *
 * Habbi only ever appears to celebrate, to encourage, or to cover her mouth at
 * a day with nothing recorded. There is no sad pose, and there should never be
 * one.
 */

import styles from "./Habbi.module.css";

export type HabbiPose = "cheer" | "encourage" | "oops";

interface HabbiProps {
  pose: HabbiPose;
  /** Rendered width. Height follows the aspect ratio. */
  size?: number;
  /** Describes the pose to screen readers; omit for purely decorative use. */
  label?: string;
  className?: string;
}

const OUTLINE = "var(--olive)";
const EAR_FILL = "var(--blush)";
const CHEEK = "var(--rose-soft)";
const BODY_FILL = "var(--card)";

const PETAL_ANGLES = [0, 72, 144, 216, 288];

/**
 * The flower tucked at the base of Habbi's left ear.
 *
 * "Left" here is hers, so it sits on the viewer's right. Flipping it is a
 * matter of changing the translate x to 40 and mirroring the ear it hugs.
 */
function EarFlower() {
  return (
    <g transform="translate(80 36)">
      {PETAL_ANGLES.map((angle) => (
        <ellipse
          key={angle}
          cx={0}
          cy={-3.6}
          rx={2.4}
          ry={3.2}
          fill="var(--rose)"
          transform={`rotate(${angle})`}
        />
      ))}
      <circle r={2} fill="var(--gold)" />
    </g>
  );
}

const ARM_WIDTH = 13;

interface ArmSpec {
  /** Where the arm meets the body. */
  x: number;
  y: number;
  /** Direction the arm points: 0 is straight up, positive turns clockwise. */
  angle: number;
  length: number;
}

/**
 * One arm: a filled capsule with its own outline, like the feet. No hand — the
 * rounded end is the whole limb. The inner end runs past the pivot so it tucks
 * under the body, which is drawn over it.
 */
function Arm({ x, y, angle, length }: ArmSpec) {
  return (
    <rect
      x={-ARM_WIDTH / 2}
      y={-length}
      width={ARM_WIDTH}
      height={length + 10}
      rx={ARM_WIDTH / 2}
      fill={BODY_FILL}
      stroke={OUTLINE}
      strokeWidth={4}
      transform={`translate(${x} ${y}) rotate(${angle})`}
    />
  );
}

/** Arms are the only part that changes between poses. */
const ARMS: Record<HabbiPose, [ArmSpec, ArmSpec]> = {
  cheer: [
    { x: 43, y: 110, angle: -42, length: 32 },
    { x: 77, y: 110, angle: 42, length: 32 },
  ],
  encourage: [
    { x: 42, y: 112, angle: -150, length: 24 },
    { x: 78, y: 108, angle: 34, length: 32 },
  ],
  // Both arms up over her mouth — an "oops". Drawn in front of the face.
  oops: [
    { x: 43, y: 112, angle: 27, length: 26 },
    { x: 77, y: 112, angle: -27, length: 26 },
  ],
};

/** Poses whose arms sit over the face rather than behind the body. */
const ARMS_IN_FRONT: Record<HabbiPose, boolean> = {
  cheer: false,
  encourage: false,
  oops: true,
};

function Arms({ pose }: { pose: HabbiPose }) {
  const [left, right] = ARMS[pose];
  return (
    <g>
      <Arm {...left} />
      <Arm {...right} />
    </g>
  );
}

export function Habbi({ pose, size = 120, label, className }: HabbiProps) {
  const decorative = label === undefined;

  return (
    <svg
      viewBox="0 0 120 152"
      width={size}
      height={(size * 152) / 120}
      className={[styles.habbi, styles[pose], className].filter(Boolean).join(" ")}
      role={decorative ? "presentation" : "img"}
      aria-hidden={decorative || undefined}
      aria-label={label}
    >
      {label ? <title>{label}</title> : null}

      {/* Ears — outer shape, then a softer inner shape. */}
      <g stroke={OUTLINE} strokeWidth={4}>
        <ellipse
          cx={47}
          cy={30}
          rx={9}
          ry={23}
          fill={BODY_FILL}
          transform="rotate(-9 47 30)"
        />
        <ellipse
          cx={73}
          cy={30}
          rx={9}
          ry={23}
          fill={BODY_FILL}
          transform="rotate(9 73 30)"
        />
        <ellipse
          cx={47}
          cy={32}
          rx={4}
          ry={15}
          fill={EAR_FILL}
          strokeWidth={0}
          transform="rotate(-9 47 32)"
        />
        <ellipse
          cx={73}
          cy={32}
          rx={4}
          ry={15}
          fill={EAR_FILL}
          strokeWidth={0}
          transform="rotate(9 73 32)"
        />
      </g>

      <EarFlower />

      {ARMS_IN_FRONT[pose] ? null : <Arms pose={pose} />}

      {/* Body, drawn over the arms so their inner ends tuck under it, and
          before the head so the head sits in front. */}
      <ellipse
        cx={60}
        cy={118}
        rx={23}
        ry={22}
        fill={BODY_FILL}
        stroke={OUTLINE}
        strokeWidth={4}
      />

      {/* Head */}
      <ellipse
        cx={60}
        cy={74}
        rx={31}
        ry={28}
        fill={BODY_FILL}
        stroke={OUTLINE}
        strokeWidth={4}
      />

      {/* Cheeks */}
      <ellipse cx={42} cy={82} rx={6} ry={3.6} fill={CHEEK} />
      <ellipse cx={78} cy={82} rx={6} ry={3.6} fill={CHEEK} />

      {/* Eyes. Curved and closed when cheering — a proper happy squint. */}
      {pose === "cheer" ? (
        <g stroke={OUTLINE} strokeWidth={3.4} strokeLinecap="round" fill="none">
          <path d="M45 74 q5 -6 10 0" />
          <path d="M65 74 q5 -6 10 0" />
        </g>
      ) : (
        <g fill={OUTLINE}>
          <circle cx={50} cy={73} r={3.2} />
          <circle cx={70} cy={73} r={3.2} />
        </g>
      )}

      {/* Nose and muzzle */}
      <ellipse cx={60} cy={84} rx={3} ry={2.2} fill="var(--rose)" />
      <path
        d="M60 86 q-5 5 -9 1 M60 86 q5 5 9 1"
        stroke={OUTLINE}
        strokeWidth={2.6}
        strokeLinecap="round"
        fill="none"
      />

      {/* Feet */}
      <ellipse cx={48} cy={138} rx={9} ry={5} fill={BODY_FILL} stroke={OUTLINE} strokeWidth={3.5} />
      <ellipse cx={72} cy={138} rx={9} ry={5} fill={BODY_FILL} stroke={OUTLINE} strokeWidth={3.5} />

      {/* The oops arms come up over the muzzle, so they go on last. */}
      {ARMS_IN_FRONT[pose] ? <Arms pose={pose} /> : null}
    </svg>
  );
}
