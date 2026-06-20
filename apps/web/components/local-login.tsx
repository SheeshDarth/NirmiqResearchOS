"use client";

import { PRODUCT_NAME, PRODUCT_TAGLINE } from "../app/page-model";

export function LocalLogin({
  displayName,
  email,
  phone,
  onDisplayNameChange,
  onEmailChange,
  onPhoneChange,
  onContinue,
}: {
  displayName: string;
  email: string;
  phone: string;
  onDisplayNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onContinue: () => void;
}) {
  const canContinue = displayName.trim().length > 0 && (email.trim().length > 0 || phone.trim().length > 0);

  return (
    <main className="login-shell">
      <section className="login-card landing-card minimal-login">
        <div className="brand-lockup hero">
          <div className="brand-mark" aria-hidden="true">
            <img alt="" src="/brand/nirmiq-ais-mark.svg" />
          </div>
          <div>
            <strong>{PRODUCT_NAME}</strong>
            <span>{PRODUCT_TAGLINE}</span>
          </div>
        </div>
        <div className="landing-copy">
          <p className="eyebrow">Local study intelligence</p>
          <h1>Chat with your study material.</h1>
          <p className="copy">
            Upload PDFs, notes, papers, question banks, or images. Ask naturally and get answers
            grounded in your own sources with citations.
          </p>
          <div className="login-proof" aria-label="NIRMIQ trust proof">
            <span>offline core</span>
            <span>citation trail</span>
            <span>abstains when unsupported</span>
            <span>paper + exam labs</span>
          </div>
          <div className="why-nirmiq">
            <strong>Not just a PDF chatbot.</strong>
            <p>
              NIRMIQ is built for academic work: verify sources, draft cited sections, prepare
              exams, and prove when the uploaded material is not enough.
            </p>
          </div>
        </div>
        <div className="login-panel">
          <h2>Start a local study thread</h2>
          <p className="tiny">
            Local profile only. No cloud account, no API key, no hosted auth.
          </p>
          <div className="login-fields">
            <label className="label">
              Name
              <input
                className="input"
                onChange={(event) => onDisplayNameChange(event.target.value)}
                placeholder="Siddharth"
                value={displayName}
              />
            </label>
            <label className="label">
              Email
              <input
                className="input"
                onChange={(event) => onEmailChange(event.target.value)}
                placeholder="you@example.com"
                type="email"
                value={email}
              />
            </label>
            <label className="label">
              Phone
              <input
                className="input"
                onChange={(event) => onPhoneChange(event.target.value)}
                placeholder="+91..."
                type="tel"
                value={phone}
              />
            </label>
          </div>
          <button className="button primary" disabled={!canContinue} onClick={onContinue} type="button">
            Open NIRMIQ
          </button>
        </div>
      </section>
    </main>
  );
}
