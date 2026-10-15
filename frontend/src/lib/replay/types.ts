import type { components } from "@/lib/api/client";

type S = components["schemas"];

/** Gap or interval as delivered: milliseconds, text such as "+1 LAP", or null. */
export type GapValue = number | string | null;

export type Runs<T> = { at: number[]; v: T[] };

export type DriverFrames = {
  pos: (number | null)[];
  gap: GapValue[];
  int: GapValue[];
  lap: Runs<number | null>;
  tyre: Runs<string | null>;
  age: Runs<number | null>;
  pit: Runs<number>;
};

export type ReplayDriver = S["ReplayDriver"];
export type ReplayEvent = S["ReplayEvent"];
export type ReplayEventKind = S["ReplayEventKindEnum"];
export type ReplayLaps = S["ReplayLaps"];

export type ReplayDoc = {
  session: S["ReplaySession"];
  drivers: ReplayDriver[];
  frames: { step_s: number; count: number; t: number[]; drivers: DriverFrames[] };
  events: ReplayEvent[];
};

export type RowState = {
  driverIndex: number;
  driverId: number;
  position: number | null;
  gap: GapValue;
  interval: GapValue;
  lap: number | null;
  tyre: string | null;
  tyreAge: number | null;
  inPit: boolean;
  /** Stops completed or in progress up to this frame. */
  pitStops: number;
  retired: boolean;
};

export type FrameState = {
  /** Index of the frame in effect (carry-forward). */
  index: number;
  /** Time of that frame, seconds. */
  frameT: number;
  /** Rows ordered by position (unknown positions last, then by driver order). */
  rows: RowState[];
  /** Lap of the race leader (highest lap among rows). */
  leaderLap: number | null;
};
