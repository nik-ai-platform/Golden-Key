import CreditCardOutlinedIcon from "@mui/icons-material/CreditCardOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import { Alert, Box, Button, Chip, CircularProgress, Divider, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  getPlans,
  annualSavingsLabel,
  formatPlanPrice,
  createBillingPortalSession,
  createCheckoutSession,
  getSubscription,
  redirectToExternal,
  type SubscriptionPlan,
} from "../services/subscriptionService";

export function SubscriptionSection() {
  const [searchParams] = useSearchParams();
  const checkoutState = searchParams.get("checkout");
  const [pendingPlan, setPendingPlan] = useState<SubscriptionPlan | null>(null);
  const [portalPending, setPortalPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const [pollAttempts, setPollAttempts] = useState(0);
  const plansQuery = useQuery({ queryKey: ["subscriptions", "plans"], queryFn: getPlans, retry: false });
  const subscriptionQuery = useQuery({
    queryKey: ["subscriptions", "me"],
    queryFn: getSubscription,
    retry: false,
    staleTime: 0,
  });
  const { data: canonicalSubscription, isFetching: accessFetching, refetch: refreshSubscription } = subscriptionQuery;
  const checkoutDisabled = pendingPlan !== null || subscriptionQuery.isPending ||
    subscriptionQuery.isError || accessFetching || canonicalSubscription?.active !== false;

  useEffect(() => {
    if (checkoutState !== "success" || canonicalSubscription?.active === true || pollAttempts >= 10 || accessFetching) return;
    const timer = window.setTimeout(() => {
      setPollAttempts((attempts) => attempts + 1);
      void refreshSubscription();
    }, 2000);
    return () => window.clearTimeout(timer);
  }, [checkoutState, canonicalSubscription?.active, accessFetching, refreshSubscription, pollAttempts]);

  async function startCheckout(plan: SubscriptionPlan) {
    if (checkoutDisabled) return;
    setActionError("");
    setPendingPlan(plan);
    try {
      const session = await createCheckoutSession(plan);
      redirectToExternal(session.url);
    } catch {
      setActionError("Unable to start checkout. Please try again.");
      setPendingPlan(null);
    }
  }

  async function manageBilling() {
    if (portalPending) return;
    setActionError("");
    setPortalPending(true);
    try {
      const session = await createBillingPortalSession();
      redirectToExternal(session.url);
    } catch {
      setActionError("Billing management is unavailable for this account.");
      setPortalPending(false);
    }
  }

  const subscription = subscriptionQuery.data;
  const hasStripeSubscription = subscription?.provider_subscriptions.some(
    (item) => item.provider === "stripe",
  ) ?? false;

  return (
    <Stack spacing={2.5} aria-labelledby="subscription-heading">
      <Box>
        <Typography id="subscription-heading" variant="h6" fontWeight={700}>
          Bear A Hand Pro
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Choose a billing interval or manage your current subscription.
        </Typography>
      </Box>

      {checkoutState === "success" ? (
        <Alert severity={subscription?.active === true && !subscriptionQuery.isError ? "success" : pollAttempts >= 10 ? "warning" : "info"}>
          {subscription?.active === true && !subscriptionQuery.isError
            ? "Premium access confirmed."
            : pollAttempts >= 10
              ? "Access is not confirmed yet. Processing may be delayed. Refresh access or contact support; do not repeat checkout to resolve this."
              : "Checkout returned. Processing subscription access—waiting for server confirmation. This does not confirm a payment."}
        </Alert>
      ) : null}
      {checkoutState === "canceled" ? (
        <Alert severity="info">Checkout was canceled. Current access is shown below.</Alert>
      ) : null}
      {checkoutState === "failed" || checkoutState === "failure" ? <Alert severity="error">Checkout could not be completed. Review your current subscription before retrying.</Alert> : null}
      <Button onClick={() => { setPollAttempts(0); void subscriptionQuery.refetch(); }} disabled={subscriptionQuery.isFetching}>Refresh access</Button>

      {subscriptionQuery.isPending ? (
        <Stack direction="row" spacing={1.5} alignItems="center">
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">Loading subscription...</Typography>
        </Stack>
      ) : null}
      {subscriptionQuery.isError ? (
        <Alert severity="error">Unable to load subscription status. Please try again.</Alert>
      ) : null}

      {subscription ? (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
          <Chip
            label={subscription.active && !subscriptionQuery.isError ? "Premium active" : "Free Preview access"}
            color={subscription.active ? "primary" : "default"}
          />
          <Typography fontWeight={600}>{plansQuery.data?.plans.find((plan) => plan.id === subscription.plan)?.name ?? (subscription.plan === "free" ? "Free Preview" : "Current plan")}</Typography>
        </Stack>
      ) : null}

      <Divider />

      {subscription?.active === true ? (
        <Typography role="status" variant="body2">
          Premium access is already active. Use billing management for your existing subscription.
        </Typography>
      ) : null}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        {plansQuery.data?.plans.map(
          (details) => (
            <Box key={details.id} sx={{ flex: 1, border: 1, borderColor: "divider", borderRadius: 1, p: 2 }}>
              <Typography fontWeight={700}>{details.name}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
                {formatPlanPrice(details.amount_minor, plansQuery.data.currency)} / {details.interval}
              </Typography>
              <Button
                fullWidth
                variant={details.id === "pro_annual" ? "contained" : "outlined"}
                startIcon={<CreditCardOutlinedIcon />}
                disabled={checkoutDisabled}
                onClick={() => void startCheckout(details.id)}
              >
                {pendingPlan === details.id ? "Opening checkout..." : `Choose ${details.interval === "month" ? "Monthly" : "Annual"}`}
              </Button>
            </Box>
          ),
        )}
      </Stack>
      {plansQuery.isPending ? <Typography role="status">Loading plans...</Typography> : null}
      {plansQuery.isError ? <Alert severity="error" action={<Button onClick={() => void plansQuery.refetch()}>Retry plans</Button>}>Unable to load plans. Checkout is unavailable until prices can be verified.</Alert> : null}
      {plansQuery.data ? <Typography variant="body2" color="text.secondary">
        {plansQuery.data.trial_days}-day trial. The selected plan renews automatically at the displayed price per interval after the trial unless canceled before renewal. Cancel through Manage Billing; access follows your subscription end date. Review final checkout terms. Billing is currently under sandbox validation, not a claim of live payment availability.
      </Typography> : null}
      {plansQuery.data && annualSavingsLabel(plansQuery.data.plans) ? <Typography variant="body2">
        {annualSavingsLabel(plansQuery.data.plans)}
      </Typography> : null}
      {subscription?.ends_at ? <Typography variant="body2">Access end: {new Date(subscription.ends_at).toLocaleString()}</Typography> : null}

      {hasStripeSubscription ? (
        <Button
          variant="text"
          startIcon={<OpenInNewOutlinedIcon />}
          disabled={portalPending}
          onClick={() => void manageBilling()}
          sx={{ alignSelf: "flex-start" }}
        >
          {portalPending ? "Opening billing..." : "Manage Billing"}
        </Button>
      ) : null}

      {actionError ? <Alert severity="error">{actionError}</Alert> : null}
    </Stack>
  );
}