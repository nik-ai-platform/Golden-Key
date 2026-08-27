import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = __ENV.BASE_URL || "http://localhost:8000";
const token = __ENV.TOKEN || "";
const profile = __ENV.LOAD_PROFILE || "mixed";

const readonlyPredictionsVus = Number(__ENV.READONLY_PREDICTIONS_VUS || 100);
const readonlyDashboardVus = Number(__ENV.READONLY_DASHBOARD_VUS || 50);
const mixedPredictionsVus = Number(__ENV.MIXED_PREDICTIONS_VUS || 100);
const mixedDashboardVus = Number(__ENV.MIXED_DASHBOARD_VUS || 50);
const importsVus = Number(__ENV.IMPORTS_VUS || 20);
const mixedImportsVus = Number(__ENV.MIXED_IMPORTS_VUS || 10);
const scenarioDuration = __ENV.SCENARIO_DURATION || "30s";

const headers = token
  ? { Authorization: `Bearer ${token}` }
  : {};

function scenariosForProfile(currentProfile) {
  if (currentProfile === "readonly-ramp") {
    return {
      predictions: {
        executor: "ramping-vus",
        startVUs: 20,
        stages: [
          { duration: "20s", target: 40 },
          { duration: "20s", target: 80 },
          { duration: "20s", target: 120 },
          { duration: "20s", target: 0 },
        ],
        exec: "predictionsScenario",
      },
      dashboard: {
        executor: "ramping-vus",
        startVUs: 10,
        stages: [
          { duration: "20s", target: 20 },
          { duration: "20s", target: 40 },
          { duration: "20s", target: 60 },
          { duration: "20s", target: 0 },
        ],
        exec: "dashboardScenario",
      },
    };
  }

  if (currentProfile === "readonly") {
    return {
      predictions: {
        executor: "constant-vus",
        vus: readonlyPredictionsVus,
        duration: scenarioDuration,
        exec: "predictionsScenario",
      },
      dashboard: {
        executor: "constant-vus",
        vus: readonlyDashboardVus,
        duration: scenarioDuration,
        exec: "dashboardScenario",
      },
    };
  }

  if (currentProfile === "imports") {
    return {
      imports: {
        executor: "constant-vus",
        vus: importsVus,
        duration: scenarioDuration,
        exec: "importsScenario",
      },
    };
  }

  return {
    predictions: {
      executor: "constant-vus",
      vus: mixedPredictionsVus,
      duration: scenarioDuration,
      exec: "predictionsScenario",
    },
    dashboard: {
      executor: "constant-vus",
      vus: mixedDashboardVus,
      duration: scenarioDuration,
      exec: "dashboardScenario",
    },
    imports: {
      executor: "constant-vus",
      vus: mixedImportsVus,
      duration: scenarioDuration,
      exec: "importsScenario",
    },
  };
}

export const options = {
  scenarios: scenariosForProfile(profile),
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<800"],
  },
};

export function predictionsScenario() {
  const response = http.get(`${baseUrl}/api/v1/predictions/1`, { headers });
  check(response, {
    "prediction status is expected": (r) => r.status === 200 || r.status === 404,
  });
  sleep(0.1);
}

export function dashboardScenario() {
  const response = http.get(`${baseUrl}/api/v1/dashboard`, { headers });
  check(response, {
    "dashboard status is 200": (r) => r.status === 200,
  });
  sleep(0.2);
}

export function importsScenario() {
  const response = http.post(
    `${baseUrl}/api/v1/imports/basketball_nba`,
    null,
    { headers },
  );
  check(response, {
    "imports status is expected": (r) => r.status === 200 || r.status === 202 || r.status === 405,
  });
  sleep(0.5);
}
