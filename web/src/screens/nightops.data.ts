// Not in Figr: built plainly from design tokens
// SIMULATED data for the night operations desk (/ops). Every row here is synthetic (rule 8).
// Rule 4: fleets see alerts and rest events only. No transcripts, no summaries, no live map.
// Last known location is present only on drivers with an active alert.

export type DriverState =
  | "talking"
  | "resting"
  | "before_dark"
  | "in_dark"
  | "promised_stop"
  | "no_response"
  | "family_unreachable"
  | "unregistered";

export type Tone = "safe" | "warn" | "danger" | "neutral";

export const STATE_META: Record<DriverState, { label: string; tone: Tone }> = {
  talking: { label: "Talking", tone: "safe" },
  resting: { label: "Resting", tone: "safe" },
  before_dark: { label: "Before dark stretch", tone: "warn" },
  in_dark: { label: "In dark stretch", tone: "warn" },
  promised_stop: { label: "Promised stop", tone: "warn" },
  no_response: { label: "No response", tone: "danger" },
  family_unreachable: { label: "Family not reachable", tone: "danger" },
  // R13: a driver who is not registered to the truck. Alerts go to the fleet night desk.
  unregistered: { label: "Unregistered driver", tone: "neutral" },
};

export type Driver = {
  id: string;
  name: string;
  sub?: string;
  truck: string;
  route: string;
  state: DriverState;
  /** Short operational note. Never a transcript or a summary of what the driver said. */
  note: string;
  /** Only rows with an active alert carry a last known location (rule 4). */
  activeAlert?: boolean;
  lastKnown?: { place: string; time: string };
};

export const DRIVERS: Driver[] = [
  {
    id: "d1",
    name: "Raju Yadav",
    truck: "MH 12 AB 1234",
    route: "NH-44 · Nagpur → Jhansi",
    state: "talking",
    note: "On a Khalasi call since 12:38 am",
  },
  {
    id: "d2",
    name: "Suresh Kumar",
    truck: "HR 55 AC 7712",
    route: "NH-48 · Jaipur → Delhi",
    state: "resting",
    note: "Rest event · dhaba since 11:50 pm",
  },
  {
    id: "d3",
    name: "Gurpreet Singh",
    truck: "PB 10 CD 3390",
    route: "NH-44 · Ambala → Agra",
    state: "before_dark",
    note: "Dark stretch begins in about 20 min",
  },
  {
    id: "d4",
    name: "Mahesh Patil",
    truck: "MH 14 EF 2210",
    route: "NH-65 · Pune → Solapur",
    state: "in_dark",
    note: "Next check-in call at 1:00 am",
  },
  {
    id: "d5",
    name: "Ravi Verma",
    truck: "UP 32 GH 9087",
    route: "NH-19 · Kanpur → Varanasi",
    state: "promised_stop",
    note: "Promised a stop by 1:10 am",
  },
  {
    id: "d6",
    name: "Anil Sahu",
    truck: "CG 04 JK 5561",
    route: "NH-53 · Raipur → Nagpur",
    state: "no_response",
    note: "No answer for dhai minute · calling primary contact",
    activeAlert: true,
    lastKnown: { place: "NH-53, near Bhandara", time: "12:41 am" },
  },
  {
    id: "d7",
    name: "Dinesh Jadhav",
    truck: "MH 04 LM 7788",
    route: "NH-48 · Mumbai → Surat",
    state: "family_unreachable",
    note: "Primary and backup not reachable · desk to call",
    activeAlert: true,
    lastKnown: { place: "NH-48, near Vapi", time: "12:36 am" },
  },
  {
    id: "d8",
    name: "Unknown",
    sub: "Not registered to this truck",
    truck: "KA 51 NP 1120",
    route: "NH-44 · Bengaluru → Hyderabad",
    state: "unregistered",
    note: "R13 · alerts for this truck go to the fleet desk",
  },
  {
    id: "d9",
    name: "Ramesh Choudhary",
    truck: "RJ 14 QR 4410",
    route: "NH-62 · Jodhpur → Jaipur",
    state: "resting",
    note: "Rest event · parked since 10:45 pm",
  },
  {
    id: "d10",
    name: "Vikram Reddy",
    truck: "TS 08 ST 6632",
    route: "NH-65 · Hyderabad → Vijayawada",
    state: "talking",
    note: "On a Khalasi call since 12:44 am",
  },
  {
    id: "d11",
    name: "Sanjay Meena",
    truck: "MP 09 UV 2275",
    route: "NH-46 · Indore → Bhopal",
    state: "in_dark",
    note: "Dark stretch until about 1:30 am",
  },
  {
    id: "d12",
    name: "Harish Nair",
    truck: "KL 07 WX 8841",
    route: "NH-66 · Kochi → Mangaluru",
    state: "before_dark",
    note: "Dark stretch begins in about 40 min",
  },
];

export type AlertReason = "not_answering" | "unreachable" | "no_network";
export type ChainStep = "primary" | "backup" | "fleet_desk";

export const REASON_LABEL: Record<AlertReason, string> = {
  not_answering: "Not answering",
  unreachable: "Unreachable",
  no_network: "No network",
};

export const CHAIN_STEPS: ChainStep[] = ["primary", "backup", "fleet_desk"];
export const STEP_LABEL: Record<ChainStep, string> = {
  primary: "Primary contact",
  backup: "Backup contact",
  fleet_desk: "Fleet desk",
};

export type Alert = {
  id: string;
  /** IST, 12-hour. */
  time: string;
  driver: string;
  truck: string;
  reason: AlertReason;
  step: ChainStep;
  resolution: string;
  open: boolean;
};

export const ALERTS: Alert[] = [
  {
    id: "a1",
    time: "12:44 am",
    driver: "Anil Sahu",
    truck: "CG 04 JK 5561",
    reason: "not_answering",
    step: "primary",
    resolution: "Open · calling primary contact, waiting for an answer",
    open: true,
  },
  {
    id: "a2",
    time: "12:39 am",
    driver: "Dinesh Jadhav",
    truck: "MH 04 LM 7788",
    reason: "unreachable",
    step: "fleet_desk",
    resolution: "Open · family not reachable, handed to the fleet desk",
    open: true,
  },
  {
    id: "a3",
    time: "12:37 am",
    driver: "Dinesh Jadhav",
    truck: "MH 04 LM 7788",
    reason: "unreachable",
    step: "backup",
    resolution: "Backup contact did not pick up · moved to fleet desk",
    open: false,
  },
  {
    id: "a4",
    time: "12:34 am",
    driver: "Dinesh Jadhav",
    truck: "MH 04 LM 7788",
    reason: "unreachable",
    step: "primary",
    resolution: "Primary contact did not pick up · moved to backup",
    open: false,
  },
  {
    id: "a5",
    time: "11:58 pm",
    driver: "Ravi Verma",
    truck: "UP 32 GH 9087",
    reason: "no_network",
    step: "primary",
    resolution: "Resolved · driver back on network, answered the call-back",
    open: false,
  },
  {
    id: "a6",
    time: "11:12 pm",
    driver: "Suresh Kumar",
    truck: "HR 55 AC 7712",
    reason: "not_answering",
    step: "primary",
    resolution: "Resolved · contact marked safe · false alarm: no",
    open: false,
  },
  {
    id: "a7",
    time: "10:20 pm",
    driver: "Gurpreet Singh",
    truck: "PB 10 CD 3390",
    reason: "not_answering",
    step: "primary",
    resolution: "Resolved · driver answered the call-back before the contact picked up",
    open: false,
  },
];
