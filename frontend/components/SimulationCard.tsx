interface Props {

    probability:number;

    margin:number;

    runs:number;

}

export default function SimulationCard({
    probability,
    margin,
    runs

}:Props){

return (

<div className="border rounded-lg p-4">

<h3>
Simulation
</h3>

<p>
Probability:
{probability}%
</p>

<p>
Projected Margin:
{margin}
</p>

<p>
Runs:
{runs}
</p>

</div>

);

}
