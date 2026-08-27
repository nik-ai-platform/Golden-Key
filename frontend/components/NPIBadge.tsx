interface Props {

    score:number;

}

export default function NPIBadge({
    score
}:Props){

    let label =
        "Weak";

    if(score >= 150)
        label="Elite";

    else if(score >=100)
        label="Strong";

    else if(score >=75)
        label="Average";

    return (

        <div className="rounded-lg border p-3">

            <div>
                NPI Score
            </div>

            <div className="text-3xl font-bold">

                {score}/200

            </div>

            <div>

                {label}

            </div>

        </div>

    );

}
