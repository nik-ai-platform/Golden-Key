import { Alert, Link, Stack, Typography } from "@mui/material";
import { useLocation } from "react-router-dom";

const documents: Record<string, { title: string; sections: [string, string][] }> = {
  "/terms": { title: "Terms of service", sections: [
    ["Use and eligibility", "Bear A Hand Sports provides sports analytics and educational information, not wagering execution or financial advice. Use only if you are of legal age and permitted to use this service where you live. You are responsible for local laws and your decisions."],
    ["Accounts and access", "Keep your credentials secure and account details accurate. Free Preview excludes selections, odds and Premium analysis. Premium requires a current server-confirmed entitlement. Do not redistribute paid content or attempt to bypass access controls."],
    ["Billing and cancellation", "Plan prices, trial length and renewal interval are shown from the service's shared plan configuration before checkout. A trial converts to the selected recurring plan unless canceled before renewal. Manage cancellation and payment methods through your account's billing management. Cancellation does not itself promise a refund; contact support for billing disputes or requests. Mandatory statutory rights remain unaffected."],
    ["Uncertainty and availability", "Models, odds and data may be incomplete, delayed or wrong. Availability and outcomes are not guaranteed. No content guarantees a win or profit. Specific liability, dispute, refund and governing-law provisions require attorney approval before public commercial use."],
  ] },
  "/privacy": { title: "Privacy notice", sections: [
    ["Data used to operate accounts", "Account registration uses email, username and credentials. Account recovery may use a secondary email and verification codes. Service operations may process account activity, saved selections, subscription status and technical diagnostics to provide and secure the product."],
    ["Billing and processors", "Hosted payment and billing flows are provided by a payment processor. Do not send full payment-card details to support. The final processor, hosting, email-delivery and analytics disclosures must be verified against production configuration before launch."],
    ["Choices and requests", "Use your profile for password and recovery-email controls and billing management for subscription controls. Contact support for access, correction or deletion requests. Identity checks and applicable legal obligations may affect fulfillment. This draft does not assert a retention duration or completed deletion workflow."],
    ["Launch review", "Attorney and operations review must finalize the controller's identity, contact address, jurisdictions, lawful bases, processor list, international transfers, retention schedule and privacy rights. This draft does not authorize additional tracking or change existing retention."],
  ] },
  "/responsible-gaming": { title: "Responsible gaming", sections: [
    ["Keep control", "Never wager money you cannot afford to lose. Set time and spending limits, do not borrow to gamble, and do not chase losses. No model score removes uncertainty or risk."],
    ["Get help", "If gambling is causing stress or harm, stop and seek qualified local support. In the United States, call 1-800-MY-RESET for gambling support; in other locations use your local public-health or gambling-support service. Contact a licensed operator for exclusion tools. Bear A Hand Sports is not a gambling operator."],
    ["Adults only", "Do not use analytics to encourage underage or unlawful gambling. Consult the laws and legal-age requirements in your jurisdiction."],
  ] },
  "/disclaimer": { title: "Prediction disclaimer", sections: [
    ["Information, not guarantees", "Predictions and analyses are estimates for education and information. NPI, Confidence Rating, Model Probability and Projected Edge describe different signals; none guarantees an outcome. Model probabilities may be miscalibrated and historical performance does not predict future results."],
    ["Data limitations", "Odds change, data can be stale, and games may be postponed or canceled. Independently verify relevant information. Parlays increase uncertainty; legs can be correlated and combined probabilities are not assurances of a win."],
    ["Your decision", "We do not place wagers, hold betting funds or provide personalized financial advice. You remain responsible for any action taken using this information."],
  ] },
  "/support": { title: "Support", sections: [
    ["Account and billing help", "For sign-in, verification, recovery, subscription or billing questions, prepare a short description and relevant timestamps. Never include passwords, verification tokens or full card details."],
    ["Contact", "Use the email link below to open your own email application. This page does not send a message, create a support ticket or promise a response time. The operational mailbox and staffing must be confirmed before customer launch."],
  ] },
};

export function LegalPage() {
  const { pathname } = useLocation();
  const document = documents[pathname] ?? documents["/support"];
  return <Stack spacing={3} sx={{ maxWidth: 850 }}>
    <Typography component="h1" variant="h3" className="gk-editorial">{document.title}</Typography>
    <Alert severity="warning">Operational draft for attorney review—not final launch-approved legal copy. Service-owner identity, jurisdiction and applicable consumer rights must be finalized before launch.</Alert>
    {document.sections.map(([heading, text]) => <Stack key={heading} spacing={1}>
      <Typography component="h2" variant="h5">{heading}</Typography>
      <Typography sx={{ lineHeight: 1.8 }}>{text}</Typography>
    </Stack>)}
    {pathname === "/support" ? <Link href="mailto:support@nik-ai-platform.com">Email support (opens your email application)</Link> : null}
  </Stack>;
}
