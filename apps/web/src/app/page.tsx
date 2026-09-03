"use client";

import { AnalysisForm } from "@/components/analysis-form";
import { LanguageSwitcher } from "@/components/language-switcher";
import { useI18n } from "@/lib/i18n";

export default function Home() {
  const { t } = useI18n();

  return (
    <main>
      <nav aria-label="Primary navigation">
        <a className="brand" href="#top">
          {t.brand}
        </a>
        <div className="nav-right">
          <span className="status">
            <i /> {t.systemsReady}
          </span>
          <LanguageSwitcher />
        </div>
      </nav>

      <section className="hero" id="top">
        <p className="eyebrow">{t.heroEyebrow}</p>
        <h1>
          {t.heroTitle1}
          <br />
          <span>{t.heroTitle2}</span>
        </h1>
        <p className="lede">{t.heroLede}</p>

        <ol className="judge-flow" aria-label={t.flowAriaLabel}>
          <li>
            <b>1</b> {t.flowStep1}
          </li>
          <li>
            <b>2</b> {t.flowStep2}
          </li>
          <li>
            <b>3</b> {t.flowStep3}
          </li>
        </ol>

        <AnalysisForm />

        <ol className="pipeline" aria-label={t.pipelineAriaLabel}>
          {t.stages.map((stage, index) => (
            <li key={stage}>
              <b>{String(index + 1).padStart(2, "0")}</b>
              {stage}
            </li>
          ))}
        </ol>
      </section>

      <section className="proof">
        <article>
          <p className="eyebrow">{t.principleEyebrow}</p>
          <h2>
            {t.principleTitle1}
            <br />
            {t.principleTitle2}
          </h2>
        </article>
        <div className="principle-card">
          <small>{t.capabilityLabel}</small>
          <strong>{t.capabilityTitle}</strong>
          <p>{t.capabilityDesc}</p>
        </div>
      </section>
    </main>
  );
}
