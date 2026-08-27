interface Props {

    confidence:number;

}

export default function ConfidenceMeter({
    confidence
}:Props){

    return (

        <div className="border rounded-lg p-3">

            <div>
                Confidence
            </div>

            <div className="text-2xl">

                {confidence}%

            </div>

        </div>

    );

}
