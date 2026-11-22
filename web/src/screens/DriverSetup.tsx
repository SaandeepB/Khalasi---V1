// Not in Figr: built plainly from design tokens
// Driver setup (/setup). Mobile web, Hindi first with English below every label (rule 9).
// Local state only: nothing is sent or saved anywhere (demo). The Khalasi number is a placeholder (rule 8).
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Headphones,
  Phone,
  PhoneCall,
  ShieldCheck,
  Smartphone,
  UserRound,
} from "lucide-react";

// Placeholder: the real Khalasi number comes from the backend. Never commit a real number.
const KHALASI_NUMBER = "+91 00000 00000";
const KHALASI_TEL = "tel:+910000000000";

const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink";

type Lang = { code: string; native: string; en: string };
const LANGUAGES: Lang[] = [
  { code: "hi", native: "हिन्दी", en: "Hindi" },
  { code: "en", native: "English", en: "English" },
  { code: "pa", native: "ਪੰਜਾਬੀ", en: "Punjabi" },
  { code: "mr", native: "मराठी", en: "Marathi" },
  { code: "ta", native: "தமிழ்", en: "Tamil" },
  { code: "te", native: "తెలుగు", en: "Telugu" },
  { code: "kn", native: "ಕನ್ನಡ", en: "Kannada" },
  { code: "bn", native: "বাংলা", en: "Bengali" },
];

const STEPS: { hi: string; en: string }[] = [
  { hi: "Bhasha", en: "Language" },
  { hi: "Sampark", en: "Contact" },
  { hi: "Sehmati", en: "Consent" },
  { hi: "Test call", en: "Test call" },
];

// Rule 9: "2½ minutes" is written "dhai minute" in Hindi, never as a decimal.
const CONSENT_HI =
  "Aapki jagah sirf emergency mein share hoti hai, aur sirf aapke sampark ke saath. Agar gaadi chalate hue aap dhai minute tak jawab nahi dete, toh Khalasi unhe phone karega. Calls 30 din baad delete ho jaati hain. Aapka fleet kabhi nahi sunta ki aapne kya kaha.";
const CONSENT_EN =
  "Location is shared only in an emergency, and only with your contact. If you don't answer for 2½ minutes while driving, Khalasi will call them. Calls are deleted after 30 days. Your fleet never hears what you say.";

type Step = 1 | 2 | 3 | 4 | 5; // 5 = done

const digits = (s: string) => s.replace(/\D/g, "");
const validPhone = (s: string) => /^[6-9]\d{9}$/.test(digits(s));

export default function DriverSetup() {
  const [step, setStep] = useState<Step>(1);
  const [lang, setLang] = useState<string>("hi");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [backupName, setBackupName] = useState("");
  const [backupPhone, setBackupPhone] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [contactSaved, setContactSaved] = useState(false);

  const backupEmpty = backupName.trim() === "" && backupPhone.trim() === "";
  const backupOk = backupEmpty || (backupName.trim() !== "" && validPhone(backupPhone));
  const contactOk = contactName.trim() !== "" && validPhone(contactPhone) && backupOk;

  const canNext = step === 1 ? lang !== "" : step === 2 ? contactOk : step === 3 ? agreed : true;

  const next = () => setStep((s) => (s < 5 ? ((s + 1) as Step) : s));
  const back = () => setStep((s) => (s > 1 ? ((s - 1) as Step) : s));
  const restart = () => {
    setStep(1);
    setLang("hi");
    setContactName("");
    setContactPhone("");
    setBackupName("");
    setBackupPhone("");
    setAgreed(false);
    setContactSaved(false);
  };

  return (
    <div className="min-h-screen bg-night text-ink">
      <div className="mx-auto flex min-h-screen w-full max-w-md flex-col gap-4 px-4 py-5">
        <header className="flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold tracking-tight text-magenta">Khalasi</span>
            <span className="text-base text-ink-muted">Setup</span>
          </div>
          <span className="rounded-md border border-warn/50 bg-warn-deep px-2.5 py-1 text-sm font-medium text-warn">
            Simulated
          </span>
        </header>

        {step < 5 && <StepIndicator current={step} />}

        <main className="flex flex-1 flex-col gap-4">
          {step === 1 && <LanguageStep lang={lang} onPick={setLang} />}
          {step === 2 && (
            <ContactStep
              contactName={contactName}
              contactPhone={contactPhone}
              backupName={backupName}
              backupPhone={backupPhone}
              onContactName={setContactName}
              onContactPhone={setContactPhone}
              onBackupName={setBackupName}
              onBackupPhone={setBackupPhone}
            />
          )}
          {step === 3 && <ConsentStep agreed={agreed} onToggle={() => setAgreed((a) => !a)} />}
          {step === 4 && (
            <TestCallStep saved={contactSaved} onSave={() => setContactSaved(true)} onDone={next} />
          )}
          {step === 5 && <DoneState contactName={contactName} lang={lang} onRestart={restart} />}
        </main>

        {step < 4 && (
          <nav aria-label="Steps" className="grid grid-cols-[auto_1fr] gap-3">
            <button
              type="button"
              onClick={back}
              disabled={step === 1}
              className={`flex h-16 items-center justify-center gap-2 rounded-control border border-line bg-raised px-5 text-ink hover:border-line-strong disabled:opacity-40 disabled:hover:border-line ${focusRing}`}
            >
              <ArrowLeft size={20} strokeWidth={2} />
              <TwoLine hi="Peeche" en="Back" />
            </button>
            <button
              type="button"
              onClick={next}
              disabled={!canNext}
              className={`flex h-16 items-center justify-center gap-3 rounded-control bg-ink px-5 text-night hover:bg-ink-muted disabled:opacity-40 disabled:hover:bg-ink ${focusRing}`}
            >
              <TwoLine hi="Aage" en="Next" />
              <ArrowRight size={20} strokeWidth={2} />
            </button>
          </nav>
        )}
        {step === 4 && (
          <button
            type="button"
            onClick={back}
            className={`flex h-12 items-center justify-center gap-2 rounded-control border border-line px-5 text-ink-muted hover:border-line-strong hover:text-ink ${focusRing}`}
          >
            <ArrowLeft size={18} strokeWidth={2} />
            <span lang="hi">Peeche</span>
            <span className="text-sm text-ink-faint">· Back</span>
          </button>
        )}

        <footer className="mt-2 flex flex-col gap-1 text-sm text-ink-faint">
          <p lang="hi">Demo: kuch bhi save nahi hota.</p>
          <p>Demo: nothing is saved.</p>
          <p className="mt-2 font-mono">Setup · demo · Simulated</p>
        </footer>
      </div>
    </div>
  );
}

/* ---------- Step indicator ---------- */

function StepIndicator({ current }: { current: Step }) {
  return (
    <ol aria-label="Setup steps" className="grid grid-cols-4 gap-2">
      {STEPS.map((s, i) => {
        const n = i + 1;
        const done = n < current;
        const active = n === current;
        return (
          <li key={s.en} aria-current={active ? "step" : undefined} className="flex flex-col items-center gap-1.5">
            <span
              className={`grid size-9 place-items-center rounded-full border text-base font-semibold ${
                done
                  ? "border-safe/60 bg-safe-deep text-safe"
                  : active
                    ? "border-ink bg-ink text-night"
                    : "border-line bg-panel text-ink-faint"
              }`}
            >
              {done ? <Check size={18} strokeWidth={2.5} /> : n}
            </span>
            <span className="text-center leading-tight">
              <span lang="hi" className={`block text-sm font-medium ${active ? "text-ink" : "text-ink-muted"}`}>
                {s.hi}
              </span>
              <span className="block text-xs text-ink-faint">{s.en}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}

/* ---------- Step 1: language ---------- */

function LanguageStep({ lang, onPick }: { lang: string; onPick: (code: string) => void }) {
  return (
    <section aria-label="Language" className="flex flex-col gap-4">
      <Heading hi="Khalasi kis bhasha mein baat kare?" en="Which language should Khalasi speak?" />
      <div role="radiogroup" aria-label="Language" className="grid grid-cols-2 gap-3">
        {LANGUAGES.map((l) => {
          const selected = l.code === lang;
          return (
            <button
              key={l.code}
              type="button"
              role="radio"
              aria-checked={selected}
              lang={l.code}
              onClick={() => onPick(l.code)}
              className={`flex h-20 flex-col items-center justify-center rounded-control border px-3 leading-tight ${focusRing} ${
                selected
                  ? "border-teal bg-raised text-ink"
                  : "border-line bg-panel text-ink-muted hover:border-line-strong hover:text-ink"
              }`}
            >
              <span className="text-2xl font-semibold">{l.native}</span>
              <span className="mt-0.5 text-sm opacity-80">{l.en}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

/* ---------- Step 2: alert contact ---------- */

function ContactStep(props: {
  contactName: string;
  contactPhone: string;
  backupName: string;
  backupPhone: string;
  onContactName: (v: string) => void;
  onContactPhone: (v: string) => void;
  onBackupName: (v: string) => void;
  onBackupPhone: (v: string) => void;
}) {
  return (
    <section aria-label="Alert contact" className="flex flex-col gap-4">
      <Heading
        hi="Emergency mein Khalasi kise phone kare?"
        en="Who should Khalasi call in an emergency?"
      />
      <div className="flex flex-col gap-3 rounded-panel border border-line bg-panel p-4">
        <div className="flex items-center gap-2 text-base font-semibold text-ink-muted">
          <UserRound size={18} strokeWidth={2} />
          <span lang="hi">Alert sampark</span>
          <span className="text-ink-faint">· Alert contact</span>
        </div>
        <Field
          id="contact-name"
          hi="Naam"
          en="Name"
          value={props.contactName}
          onChange={props.onContactName}
          placeholder="Sunita Yadav"
        />
        <Field
          id="contact-phone"
          hi="Phone number"
          en="Phone number (10 digits)"
          value={props.contactPhone}
          onChange={props.onContactPhone}
          placeholder="98765 43210"
          tel
        />
      </div>
      <div className="flex flex-col gap-3 rounded-panel border border-line bg-panel p-4">
        <div className="flex items-center gap-2 text-base font-semibold text-ink-muted">
          <UserRound size={18} strokeWidth={2} />
          <span lang="hi">Backup sampark (zaroori nahi)</span>
          <span className="text-ink-faint">· Backup contact (optional)</span>
        </div>
        <Field
          id="backup-name"
          hi="Naam"
          en="Name"
          value={props.backupName}
          onChange={props.onBackupName}
          placeholder="Mohan Yadav"
        />
        <Field
          id="backup-phone"
          hi="Phone number"
          en="Phone number (10 digits)"
          value={props.backupPhone}
          onChange={props.onBackupPhone}
          placeholder="98765 43211"
          tel
        />
      </div>
      <p className="text-sm text-ink-faint">
        <span lang="hi">Agar pehla sampark phone na uthaye, toh Khalasi backup ko phone karega.</span>
        <br />
        If the first contact doesn't pick up, Khalasi calls the backup.
      </p>
    </section>
  );
}

function Field({
  id,
  hi,
  en,
  value,
  onChange,
  placeholder,
  tel = false,
}: {
  id: string;
  hi: string;
  en: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  tel?: boolean;
}) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1.5">
      <span className="leading-tight">
        <span lang="hi" className="block text-lg font-medium">
          {hi}
        </span>
        <span className="block text-sm text-ink-muted">{en}</span>
      </span>
      <input
        id={id}
        type={tel ? "tel" : "text"}
        inputMode={tel ? "tel" : "text"}
        autoComplete={tel ? "tel-national" : "name"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`h-14 rounded-control border border-line bg-raised px-4 text-lg text-ink outline-none placeholder:text-ink-faint focus:border-teal ${
          tel ? "font-mono tabular-nums" : ""
        }`}
      />
    </label>
  );
}

/* ---------- Step 3: consent ---------- */

function ConsentStep({ agreed, onToggle }: { agreed: boolean; onToggle: () => void }) {
  return (
    <section aria-label="Consent" className="flex flex-col gap-4">
      <Heading hi="Khalasi aise kaam karta hai" en="How Khalasi works" />
      <div className="rounded-panel border border-line bg-panel p-5">
        <div className="flex items-center gap-2 text-base font-semibold text-teal">
          <ShieldCheck size={20} strokeWidth={2} />
          <span lang="hi">Aapki jaankari, aapke haath mein</span>
        </div>
        <p lang="hi" className="mt-3 text-xl leading-snug font-medium">
          {CONSENT_HI}
        </p>
        <p className="mt-3 text-base leading-snug text-ink-muted">{CONSENT_EN}</p>
      </div>
      <button
        type="button"
        role="checkbox"
        aria-checked={agreed}
        onClick={onToggle}
        className={`flex min-h-16 items-center gap-4 rounded-control border px-4 py-3 text-left ${focusRing} ${
          agreed ? "border-safe/60 bg-safe-deep" : "border-line bg-raised hover:border-line-strong"
        }`}
      >
        <span
          className={`grid size-8 shrink-0 place-items-center rounded-md border ${
            agreed ? "border-safe bg-safe text-night" : "border-line-strong bg-night"
          }`}
        >
          {agreed && <Check size={20} strokeWidth={3} />}
        </span>
        <span className="leading-tight">
          <span lang="hi" className={`block text-lg font-semibold ${agreed ? "text-safe" : "text-ink"}`}>
            Main samajh gaya, main sehmat hoon
          </span>
          <span className="block text-sm text-ink-muted">I understand and I agree</span>
        </span>
      </button>
    </section>
  );
}

/* ---------- Step 4: save number and test call (required) ---------- */

function TestCallStep({ saved, onSave, onDone }: { saved: boolean; onSave: () => void; onDone: () => void }) {
  return (
    <section aria-label="Test call" className="flex flex-col gap-4">
      <Heading hi="Aakhri zaroori kadam" en="Last required step" />

      {/* 4a: save the number */}
      <div className="rounded-panel border border-line bg-panel p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-base font-semibold text-ink-muted">
            <Phone size={18} strokeWidth={2} />
            <span lang="hi">1. Number save karein</span>
            <span className="text-ink-faint">· Save the number</span>
          </div>
          <span className="text-sm text-ink-faint">Demo number</span>
        </div>
        <div className="mt-3 flex items-center gap-3 rounded-control border border-line bg-raised p-3">
          <div className="grid size-11 place-items-center rounded-full bg-night text-base font-semibold text-magenta">
            K
          </div>
          <div className="leading-tight">
            <div className="text-lg font-semibold">Khalasi</div>
            <div className="font-mono text-base text-ink-muted tabular-nums">{KHALASI_NUMBER}</div>
          </div>
        </div>
        <p className="mt-3 text-sm text-ink-muted">
          <span lang="hi">Is number ko phone mein "Khalasi" naam se save karein, taaki call aane par naam dikhe.</span>
          <br />
          Save this number as "Khalasi" so the name shows when Khalasi calls.
        </p>
        {/* Visual only: nothing is written to the phone's contacts. */}
        <button
          type="button"
          onClick={onSave}
          aria-pressed={saved}
          className={`mt-3 flex h-14 w-full items-center justify-center gap-3 rounded-control border px-5 ${focusRing} ${
            saved
              ? "border-safe/60 bg-safe-deep text-safe"
              : "border-line bg-raised text-ink hover:border-line-strong"
          }`}
        >
          {saved ? <Check size={20} strokeWidth={2.5} /> : <Phone size={20} strokeWidth={2} />}
          <TwoLine
            hi={saved ? "Save ho gaya (demo)" : "Contact save karein"}
            en={saved ? "Saved (demo)" : "Save contact"}
          />
        </button>
      </div>

      {/* 4b: hands-free test call */}
      <div className="rounded-panel border border-line bg-panel p-4">
        <div className="flex items-center gap-2 text-base font-semibold text-ink-muted">
          <Headphones size={18} strokeWidth={2} />
          <span lang="hi">2. Test call, bina haath lagaye</span>
          <span className="text-ink-faint">· Hands-free test call</span>
        </div>
        <ul className="mt-3 flex flex-col gap-3">
          <Tip
            icon={Headphones}
            hi="Call uthane ke liye earphone ka button dabayein, ya phone ki auto-answer setting on karein."
            en="Press the earphone button to answer, or turn on your phone's auto-answer setting."
          />
          <Tip
            icon={Smartphone}
            hi="Phone ko holder mein rakhein. Gaadi chalate hue phone haath mein na lein."
            en="Keep the phone in a holder. Don't hold the phone while driving."
          />
        </ul>
        <a
          href={KHALASI_TEL}
          className={`mt-4 flex h-16 items-center justify-center gap-3 rounded-control bg-ink px-5 text-night hover:bg-ink-muted ${focusRing}`}
        >
          <PhoneCall size={22} strokeWidth={2} />
          <TwoLine hi="Test call karein" en="Make the test call" />
        </a>
        <button
          type="button"
          onClick={onDone}
          className={`mt-3 flex h-16 w-full items-center justify-center gap-3 rounded-control border border-safe/60 bg-safe-deep px-5 text-safe hover:border-safe ${focusRing}`}
        >
          <Check size={22} strokeWidth={2.5} />
          <TwoLine hi="Test call ho gaya" en="Test call done" />
        </button>
      </div>
    </section>
  );
}

function Tip({ icon: Icon, hi, en }: { icon: typeof Headphones; hi: string; en: string }) {
  return (
    <li className="flex items-start gap-3">
      <Icon size={20} strokeWidth={2} className="mt-1 shrink-0 text-teal" />
      <div className="leading-tight">
        <p lang="hi" className="text-lg font-medium">
          {hi}
        </p>
        <p className="mt-0.5 text-sm text-ink-muted">{en}</p>
      </div>
    </li>
  );
}

/* ---------- Done ---------- */

function DoneState({
  contactName,
  lang,
  onRestart,
}: {
  contactName: string;
  lang: string;
  onRestart: () => void;
}) {
  const langName = LANGUAGES.find((l) => l.code === lang)?.en ?? "Hindi";
  return (
    <section aria-live="polite" className="animate-fade flex flex-col gap-4 motion-reduce:animate-none">
      <div className="rounded-panel border border-safe/60 bg-safe-deep p-5">
        <div className="flex items-center gap-2 text-base font-semibold text-safe">
          <ShieldCheck size={20} strokeWidth={2} />
          <span lang="hi">Sab set hai · All set</span>
        </div>
        <h1 lang="hi" className="mt-3 text-2xl leading-snug font-semibold">
          Khalasi ab raat ki drive mein aapke saath hai.
        </h1>
        <p className="mt-2 text-lg leading-snug text-ink-muted">Khalasi is with you on night drives now.</p>
      </div>
      <div className="rounded-panel border border-line bg-panel p-5 text-base">
        <ul className="flex flex-col divide-y divide-line/60">
          <Row hi="Bhasha" en="Language" value={langName} />
          <Row hi="Alert sampark" en="Alert contact" value={contactName.trim() || "—"} />
          <Row hi="Test call" en="Test call" value="Done (demo)" />
        </ul>
      </div>
      <Link
        to="/home"
        className={`flex h-16 items-center justify-center gap-3 rounded-control bg-ink px-5 text-night hover:bg-ink-muted ${focusRing}`}
      >
        <TwoLine hi="Home par jaayein" en="Go to home" />
        <ArrowRight size={20} strokeWidth={2} />
      </Link>
      <button
        type="button"
        onClick={onRestart}
        className={`flex h-12 items-center justify-center rounded-control border border-line px-5 text-ink-muted hover:border-line-strong hover:text-ink ${focusRing}`}
      >
        <span lang="hi">Phir se shuru karein</span>
        <span className="ml-2 text-sm text-ink-faint">· Start over</span>
      </button>
    </section>
  );
}

function Row({ hi, en, value }: { hi: string; en: string; value: string }) {
  return (
    <li className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
      <span className="leading-tight">
        <span lang="hi" className="block font-medium">
          {hi}
        </span>
        <span className="block text-sm text-ink-muted">{en}</span>
      </span>
      <span className="text-right font-medium">{value}</span>
    </li>
  );
}

/* ---------- Shared bits ---------- */

function Heading({ hi, en }: { hi: string; en: string }) {
  return (
    <div className="leading-tight">
      <h1 lang="hi" className="text-2xl font-semibold">
        {hi}
      </h1>
      <p className="mt-1 text-base text-ink-muted">{en}</p>
    </div>
  );
}

function TwoLine({ hi, en }: { hi: string; en: string }) {
  return (
    <span className="flex flex-col items-center leading-tight">
      <span lang="hi" className="text-lg font-semibold">
        {hi}
      </span>
      <span className="text-sm opacity-80">{en}</span>
    </span>
  );
}
