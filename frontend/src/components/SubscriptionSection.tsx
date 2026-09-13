import CreditCardOutlinedIcon from "@mui/icons-material/CreditCardOutlined";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import { Alert, Box, Button, Chip, CircularProgress, Divider, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  SUBSCRIPTION_PLANS,
  createBillingPortalSession,
  createCheckoutSession,
  getSubscription,
  redirectToExternal,
  type SubscriptionPlan,
} from "../services/subscriptionService";

function planLabel(plan: string): string {
  if (plan in SUBSCRIPTION_PLANS) {
    return SUBSCRIPTION_PLANS[plan as SubscriptionPlan].name;
  }
  return plan === "free" ? "Standard" : "Current plan";
}

export function SubscriptionSection() {
  const [searchParams] = useSearchParams();
  const checkoutState = searchParams.get("checkout");
  const [pendingPlan, setPendingPlan] = useState<SubscriptionPlan | null>(null);
  const [portalPending, setPortalPending] = useState(false);
  const [actionError, setActionError] = useState("");
  const subscriptionQuery = useQuery({
    queryKey: ["subscriptions", "me"],
    queryFn: getSubscription,
    enabled: checkoutState !== "success",
  });

  useEffect(() => {
    if (checkoutState === "success") {
      void subscriptionQuery.refetch();
    }
  }, [checkoutState, subscriptionQuery.refetch]);

  async function startCheckout(plan: SubscriptionPlan) {
    if (pendingPlan) return;
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
        <Alert severity="success">
          Your payment was completed. Updating your Bear A Hand Pro access...
        </Alert>
      ) : null}
      {checkoutState === "canceled" ? (
        <Alert severity="info">Checkout was canceled. No subscription changes were made.</Alert>
      ) : null}

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
            label={subscription.active ? "Premium active" : "Standard access"}
            color={subscription.active ? "primary" : "default"}
          />
          <Typography fontWeight={600}>{planLabel(subscription.plan)}</Typography>
        </Stack>
      ) : null}

      <Divider />

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        {(Object.entries(SUBSCRIPTION_PLANS) as [SubscriptionPlan, (typeof SUBSCRIPTION_PLANS)[SubscriptionPlan]][]).map(
          ([plan, details]) => (
            <Box key={plan} sx={{ flex: 1, border: 1, borderColor: "divider", borderRadius: 1, p: 2 }}>
              <Typography fontWeight={700}>{details.name}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
                {details.billingLabel}
              </Typography>
              <Button
                fullWidth
                variant={plan === "pro_annual" ? "contained" : "outlined"}
                startIcon={<CreditCardOutlinedIcon />}
                disabled={pendingPlan !== null}
                onClick={() => void startCheckout(plan)}
              >
                {pendingPlan === plan ? "Opening checkout..." : `Choose ${details.billingLabel}`}
              </Button>
            </Box>
          ),
        )}
      </Stack>

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