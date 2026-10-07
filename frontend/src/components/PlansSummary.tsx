import { Alert, Button, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { formatPlanPrice, getPlans } from "../services/subscriptionService";

export function PlansSummary() {
  const query = useQuery({ queryKey: ["subscriptions", "plans"], queryFn: getPlans, retry: false });
  if (query.isPending) return <Typography role="status">Loading plans...</Typography>;
  if (query.isError) return <Alert severity="error" action={<Button onClick={() => void query.refetch()}>Retry</Button>}>Plan details are unavailable. Please retry before subscribing.</Alert>;
  return <Stack spacing={1.5} sx={{ mt: 2 }}>
    {query.data.plans.map((plan) => <Typography key={plan.id}>{plan.name}: {formatPlanPrice(plan.amount_minor, query.data.currency)} / {plan.interval}</Typography>)}
    <Typography>{query.data.trial_days}-day trial. After the trial, your selected plan renews automatically at the displayed price per billing interval unless canceled before renewal. Cancel through billing management; access follows the canonical subscription end date. Review the final checkout terms before confirming.</Typography>
    {query.data.premium_benefits.map((benefit) => <Typography key={benefit} variant="body2">{benefit}</Typography>)}
  </Stack>;
}
