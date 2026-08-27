"use client";

export default function SubscriptionBadge({
plan
}: {
plan: string
}) {

return (

<div className="border rounded p-3">

Account:

<strong>
{plan.toUpperCase()}
</strong>

</div>

);

}