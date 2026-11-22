// Khalasi demo engine. Mirrors khalasi-night-call-states.mermaid.
// All times are simulated seconds since Raju's missed call at 12:10 am.

export type Speaker = "khalasi" | "raju";
export type Flag = { label: string; at: number };
export type Line = {
  id: number;
  at: number;
  speaker: Speaker;
  hi: string;
  en: string;
  flags?: Flag[];
};
export type LogKind =
  | "call"
  | "stop"
  | "nudge"
  | "callback"
  | "alert"
  | "schedule"
  | "resolve"
  | "info";
export type Tone = "neutral" | "amber" | "red" | "green";
export type LogEntry = {
  id: number;
  at: number;
  kind: LogKind;
  text: string;
  tone: Tone;
};
export type Mode =
  | "idle"
  | "talking"
  | "sleepy"
  | "pitch"
  | "promised"
  | "resting"
  | "darkBrief"
  | "darkStretch"
  | "quiet"
  | "escalating"
  | "alert"
  | "safe";
export type Truck = "moving" | "dhaba" | "highway";
export type EscKind = "noAnswer" | "unreachable";
export type Esc = { kind: EscKind; start: number; fired: number[] };
type Beat = { at: number; run: (s: Sim) => Sim };

export type Sim = {
  t: number;
  started: boolean;
  mode: Mode;
  truck: Truck;
  lines: Line[];
  log: LogEntry[];
  queue: Beat[];
  esc: Esc | null;
  signs: number;
  onCall: boolean;
  nextCallAt: number | null;
  restStart: number | null;
  lastRestAt: number;
  promiseAt: number | null;
  promiseFollowed: boolean;
  stop: string;
  seq: number;
};

export const MILESTONES = [
  { at: 15, label: "Nudge" },
  { at: 45, label: "Call-back" },
  { at: 90, label: "Second try" },
  { at: 150, label: "Sunita alerted" },
] as const;
export const ALERT_AT = 150;

// Clock: call starts 12:10 am; trip started 7:00 pm; 5h 10m since last rest.
const START_MIN = 10;
export function clock(t: number, withPeriod = true): string {
  const total = (START_MIN + Math.floor(t / 60)) % (24 * 60);
  const h24 = Math.floor(total / 60);
  const m = total % 60;
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12;
  const period = h24 < 12 ? "am" : "pm";
  return `${h12}:${m.toString().padStart(2, "0")}${withPeriod ? ` ${period}` : ""}`;
}
export function mmss(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
}
export function hm(sec: number): string {
  const min = Math.max(0, Math.floor(sec / 60));
  return `${Math.floor(min / 60)}h ${min % 60}m`;
}

export function initialSim(): Sim {
  return {
    t: 0,
    started: false,
    mode: "idle",
    truck: "moving",
    lines: [],
    log: [],
    queue: [],
    esc: null,
    signs: 0,
    onCall: false,
    nextCallAt: null,
    restStart: null,
    lastRestAt: -(5 * 60 + 10) * 60,
    promiseAt: null,
    promiseFollowed: false,
    stop: "Sharma Dhaba",
    seq: 1,
  };
}

function say(s: Sim, speaker: Speaker, hi: string, en: string, flags?: string[]): Sim {
  const line: Line = {
    id: s.seq,
    at: s.t,
    speaker,
    hi,
    en,
    flags: flags?.map((label) => ({ label, at: s.t })),
  };
  return { ...s, seq: s.seq + 1, lines: [...s.lines, line] };
}
function log(s: Sim, kind: LogKind, text: string, tone: Tone = "neutral"): Sim {
  return { ...s, seq: s.seq + 1, log: [...s.log, { id: s.seq, at: s.t, kind, text, tone }] };
}
function sign(s: Sim, count: number): Sim {
  const signs = s.signs + count;
  const mode = s.mode === "talking" ? "sleepy" : s.mode;
  return { ...s, signs, mode };
}
function schedule(s: Sim, steps: [number, (s: Sim) => Sim][]): Sim {
  const last = s.queue.length ? s.queue[s.queue.length - 1].at : s.t;
  const base = Math.max(s.t, last) + 0.5;
  return { ...s, queue: [...s.queue, ...steps.map(([d, run]) => ({ at: base + d, run }))] };
}

/* ---------- Scripts ---------- */

export function startCall(s: Sim): Sim {
  let n: Sim = { ...s, started: true, onCall: true, mode: "talking" };
  n = log(n, "call", "Missed call from Raju · Khalasi called back");
  return schedule(n, [
    [0.5, (x) => say(x, "khalasi", "Ustaad, chai pi aapne?", "Ustaad, have you had chai?")],
    [6, (x) => say(x, "raju", "Haan, Seoni mein pi thi.", "Yes, I had it at Seoni.")],
    [11, (x) => say(x, "khalasi", "Aaj Jhansi tak jaana hai na?", "You're going all the way to Jhansi today, right?")],
    [
      18,
      (x) => sign(say(x, "raju", "Haan… Jhansi.", "Yes… Jhansi.", ["Slow reply 4.2 s"]), 1),
    ],
    [25, (x) => say(x, "khalasi", "Ghar pe Sunita ji se baat hui aaj?", "Did you talk to Sunita at home today?")],
    [
      32,
      (x) =>
        sign(
          say(x, "raju", "Hmm… (jamhai) …kya poocha?", "Hmm… (yawns) …what did you ask?", [
            "Yawn",
            "Confused answer",
          ]),
          2,
        ),
    ],
    [
      38,
      (x) => {
        let n = { ...x, mode: "pitch" as Mode, stop: "Sharma Dhaba" };
        n = say(n, "khalasi", "Ustaad, agle dhabe pe truck lagao.", "Ustaad, pull over at the next dhaba.");
        return log(n, "stop", "Rest stop suggested · Sharma Dhaba, 6 km", "amber");
      },
    ],
    [42, (x) => say(x, "khalasi", "20 minute so jao.", "Sleep for 20 minutes.")],
    [
      49,
      (x) => {
        let n = say(x, "raju", "Theek hai, Sharma Dhaba pe rukta hoon.", "Okay, I'll stop at Sharma Dhaba.");
        n = { ...n, mode: "promised", promiseAt: n.t, promiseFollowed: false };
        return log(n, "schedule", `Promised stop · follow-up at ${clock(n.t + 600)} if still moving`);
      },
    ],
    [
      55,
      (x) => say(x, "khalasi", "Badhiya, Sharma Dhaba 6 km pe hai.", "Good, Sharma Dhaba is 6 km away."),
    ],
  ]);
}

export function darkStretchAhead(s: Sim): Sim {
  let n: Sim = { ...s, mode: "darkBrief", stop: "Apna Ghar" };
  n = log(n, "info", "Dark stretch in 18 min · 5h+ since last rest", "amber");
  return schedule(n, [
    [
      0.5,
      (x) =>
        say(
          x,
          "khalasi",
          `Ustaad, aap shaam 7 baje nikle the, ab raat ke ${clock(x.t, false)} ho gaye.`,
          `Ustaad, you left at 7 in the evening, and now it's ${clock(x.t, false)} at night.`,
        ),
    ],
    [6, (x) => say(x, "khalasi", "Paanch ghante se zyada ho gaye bina ruke.", "That's more than five hours without a stop.")],
    [11, (x) => say(x, "raju", "Haan, pata hai.", "Yes, I know.")],
    [
      15,
      (x) =>
        say(
          x,
          "khalasi",
          "Aage lagbhag 40 minute network nahi milega, aur Jhansi abhi 3 ghante door hai.",
          "There's no network for about 40 minutes ahead, and Jhansi is still 3 hours away.",
        ),
    ],
    [22, (x) => say(x, "khalasi", "8 km pe Apna Ghar hai.", "There's an Apna Ghar at 8 km.")],
    [26, (x) => say(x, "khalasi", "Wahan aadha ghanta ruk jao?", "Will you stop there for half an hour?")],
    [32, (x) => say(x, "raju", "Nahi, subah tak Jhansi pahunchna hai.", "No, I have to reach Jhansi by morning.")],
    [37, (x) => say(x, "khalasi", "Network aate hi main phone karunga", "I'll call you as soon as there's network")],
    [
      40,
      (x) => {
        let n: Sim = { ...x, mode: "darkStretch", onCall: false, nextCallAt: x.t + 2400 };
        n = log(n, "info", "Stop refused · rest clock not reset");
        return log(n, "schedule", `Call ended · call scheduled for stretch exit, about ${clock(x.t + 2400)}`);
      },
    ],
  ]);
}

export function driverSaysChup(s: Sim): Sim {
  return schedule(s, [
    [0.5, (x) => say(x, "raju", "Chup karo yaar, thodi der shanti chahiye.", "Quiet, yaar, I need some peace for a while.")],
    [4, (x) => say(x, "khalasi", "Theek hai, 10 minute baad baat karte hain", "Okay, let's talk in 10 minutes")],
    [
      7,
      (x) => {
        const n: Sim = { ...x, mode: "quiet", onCall: false, nextCallAt: x.t + 600 };
        return log(n, "schedule", `Quiet mode · call ended, call-back at ${clock(x.t + 600)}`);
      },
    ],
  ]);
}

export function noAnswer(s: Sim): Sim {
  if (s.truck === "dhaba") {
    const n: Sim = { ...s, mode: "resting", restStart: s.restStart ?? s.t };
    return log(n, "info", "Raju silent, truck stopped at dhaba · no escalation", "green");
  }
  const n: Sim = { ...s, queue: [], mode: "escalating", esc: { kind: "noAnswer", start: s.t, fired: [] } };
  return log(n, "info", "Raju stopped answering · truck moving", "amber");
}

export function phoneUnreachable(s: Sim): Sim {
  if (s.mode === "darkStretch") {
    return log(s, "info", "Phone unreachable inside known dark stretch · holding until it ends");
  }
  const n: Sim = {
    ...s,
    queue: [],
    onCall: false,
    mode: "escalating",
    esc: { kind: "unreachable", start: s.t, fired: [] },
  };
  return log(n, "info", "Call dropped · phone off or out of coverage", "amber");
}

export function rajuAnswers(s: Sim): Sim {
  const wasAlert = s.mode === "alert";
  let n: Sim = { ...s, esc: null, onCall: true, mode: wasAlert ? "safe" : "talking" };
  n = say(n, "raju", "Haan haan, sun raha hoon.", "Yes, yes, I'm listening.");
  n = log(n, "resolve", wasAlert ? "Raju answered · Sunita told he's safe" : "Raju answered · escalation stopped", "green");
  if (wasAlert) n = schedule(n, [[4, (x) => ({ ...x, mode: "talking" })]]);
  return n;
}

export function sunitaMarksSafe(s: Sim): Sim {
  let n: Sim = { ...s, esc: null, mode: "safe" };
  n = log(n, "resolve", "Sunita marked Raju safe · asked if it was a false alarm", "green");
  return schedule(n, [
    [
      3,
      (x) => {
        let m: Sim = { ...x, onCall: true };
        m = log(m, "call", "Khalasi calling Raju back");
        return say(m, "khalasi", "Ustaad, Sunita ji ne bataya aap theek ho.", "Ustaad, Sunita told us you're okay.");
      },
    ],
    [7, (x) => ({ ...x, mode: "talking" })],
  ]);
}

export function setTruck(s: Sim, truck: Truck): Sim {
  if (truck === s.truck) return s;
  let n: Sim = { ...s, truck };
  if (truck === "dhaba") {
    n = { ...n, queue: [], esc: null, mode: "resting", restStart: n.t, onCall: n.onCall };
    if (s.esc) return log(n, "resolve", `Stopped at ${s.stop} · escalation stopped`, "green");
    n = log(n, "stop", `Resting at ${s.stop} · rest clock resets after 30 min`, "green");
    return n;
  }
  if (s.truck === "dhaba" && s.restStart !== null) {
    const rested = n.t - s.restStart;
    const reset = rested >= 1800;
    n = { ...n, restStart: null, lastRestAt: reset ? n.t : n.lastRestAt, mode: n.mode === "resting" ? "talking" : n.mode };
    n = log(n, "info", reset ? "Back on the road · rest clock reset" : `Back on the road · rested ${mmss(rested)}, clock not reset`);
  }
  if (truck === "highway") {
    n = log(n, "info", "Stopped on highway · silence escalates as if moving", "amber");
  }
  return n;
}

/* ---------- Tick ---------- */

function fireMilestone(s: Sim, m: number): Sim {
  const e = s.esc!;
  let n: Sim = { ...s, esc: { ...e, fired: [...e.fired, m] } };
  const unreachable = e.kind === "unreachable";
  if (m === 15) {
    if (unreachable) return n;
    n =
      s.truck === "highway"
        ? say(n, "khalasi", "Ustaad, gaadi side mein hai? Sab theek?", "Ustaad, is the truck on the side? All okay?")
        : say(n, "khalasi", "Ustaad, sun rahe ho?", "Ustaad, can you hear me?");
    return log(n, "nudge", "Nudge on the call", "amber");
  }
  if (m === 45) {
    n = { ...n, onCall: false };
    return log(n, "callback", unreachable ? "Call-back · phone unreachable" : "Call-back · rang, no answer", "amber");
  }
  if (m === 90) {
    return log(n, "callback", unreachable ? "Second try · phone unreachable" : "Second try · rang, no answer", "red");
  }
  n = { ...n, mode: "alert" };
  return log(
    n,
    "alert",
    unreachable
      ? "Sunita alerted · Raju's phone is unreachable. He may be in a no-network stretch."
      : "Sunita alerted · Raju hasn't answered for 2½ minutes",
    "red",
  );
}

export function tick(prev: Sim, dt: number): Sim {
  if (!prev.started) return prev;
  let s: Sim = { ...prev, t: prev.t + dt };

  while (s.queue.length && s.queue[0].at <= s.t) {
    const [beat, ...rest] = s.queue;
    s = beat.run({ ...s, queue: rest });
  }

  if (s.esc) {
    const elapsed = s.t - s.esc.start;
    for (const m of MILESTONES) {
      if (elapsed >= m.at && !s.esc!.fired.includes(m.at)) s = fireMilestone(s, m.at);
    }
  }

  if (s.mode === "promised" && s.promiseAt !== null && !s.promiseFollowed && s.t - s.promiseAt >= 600 && s.truck !== "dhaba") {
    s = { ...s, promiseFollowed: true };
    s = say(s, "khalasi", "Ustaad, dhaba nahi aaya?", "Ustaad, no dhaba yet?");
    s = log(s, "nudge", "Promise follow-up · still moving after 10 min", "amber");
  }

  if (s.mode === "quiet" && s.nextCallAt !== null && s.t >= s.nextCallAt) {
    s = { ...s, mode: "talking", onCall: true, nextCallAt: null };
    s = log(s, "call", "Quiet mode over · Khalasi called Raju back");
    s = say(s, "khalasi", "Ustaad, ab baat karein?", "Ustaad, shall we talk now?");
  }

  return s;
}

export function runFor(s: Sim, seconds: number): Sim {
  let n = s;
  for (let i = 0; i < seconds * 4; i++) n = tick(n, 0.25);
  return n;
}

export function presetSim(preset?: string): Sim {
  if (!preset) return initialSim();
  let s = runFor(startCall(initialSim()), 58);
  if (preset === "sleep") return s;
  if (preset === "dark") return runFor(darkStretchAhead(s), 44);
  if (preset === "alert") return runFor(noAnswer(s), 158);
  if (preset === "unreachable") return runFor(phoneUnreachable(s), 158);
  return s;
}

/* ---------- Derived ---------- */

export type Level = "green" | "amber" | "red";
export function levelOf(s: Sim): Level {
  if (s.mode === "alert") return "red";
  if (s.mode === "escalating" && s.esc && s.t - s.esc.start >= 90) return "red";
  if (["sleepy", "pitch", "promised", "darkBrief", "darkStretch", "escalating"].includes(s.mode)) return "amber";
  return "green";
}

export function stateLabel(s: Sim): { title: string; detail: string } {
  switch (s.mode) {
    case "idle":
      return { title: "Waiting for a missed call", detail: "Raju is parked at Nagpur" };
    case "talking":
      return { title: "Talking", detail: "Raju sounds alert" };
    case "sleepy":
      return { title: "Sleep signs heard", detail: "A rest stop is suggested at 2 signs" };
    case "pitch":
      return { title: "Suggesting a rest stop", detail: `${s.stop}, 6 km ahead` };
    case "promised": {
      const left = s.promiseAt !== null ? 600 - (s.t - s.promiseAt) : 0;
      return {
        title: "Promised stop",
        detail: s.promiseFollowed ? "Followed up, still moving" : `Follow-up in ${mmss(left)} if still moving`,
      };
    }
    case "resting":
      return {
        title: `Resting at ${s.stop}`,
        detail: s.restStart !== null ? `Rested ${mmss(s.t - s.restStart)} · clock resets at 30:00` : "",
      };
    case "darkBrief":
      return { title: "Before the dark stretch", detail: "About 40 min with no network ahead" };
    case "darkStretch":
      return { title: "In dark stretch", detail: `Call scheduled for about ${clock(s.nextCallAt ?? s.t)}` };
    case "quiet":
      return { title: "Quiet mode", detail: `Call-back at ${clock(s.nextCallAt ?? s.t)}` };
    case "escalating":
      return {
        title: s.esc?.kind === "unreachable" ? "Phone unreachable" : "No answer",
        detail: s.truck === "highway" ? "Truck stopped on highway" : "Truck moving",
      };
    case "alert":
      return { title: "Sunita alerted", detail: "Backup contact is next" };
    case "safe":
      return { title: "Marked safe", detail: "Khalasi is calling Raju back" };
  }
}
