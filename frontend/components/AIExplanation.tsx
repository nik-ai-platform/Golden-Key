interface Props {

    explanation:string;

}

export default function AIExplanation({
    explanation
}:Props){

return (

<div className="border rounded-lg p-4">

<h3>
AI Explanation
</h3>

<p>
{explanation}
</p>

</div>

);

}
