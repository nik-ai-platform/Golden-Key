export interface Prediction {

    id:number;

    game_id:number;

    market:string;

    selection:string;

    npi_score:number;

    win_probability:number;

    confidence_score:number;

    projected_edge:number;

    risk_level:string;

    reasoning:string;

    simulation_probability:number;

    simulation_runs:number;

    simulation_margin:number;
}
