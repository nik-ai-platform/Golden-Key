import { create } from "zustand";

interface AppState {
  user: { name: string; subscription: string };
  portfolio: { bankroll: number; roi: number };
  liveGames: string[];
  alerts: string[];
  setUser: (user: AppState["user"]) => void;
  setPortfolio: (portfolio: AppState["portfolio"]) => void;
  setLiveGames: (games: string[]) => void;
  setAlerts: (alerts: string[]) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: { name: "Golden User", subscription: "PRO" },
  portfolio: { bankroll: 12500, roi: 12.4 },
  liveGames: ["Lakers vs Warriors"],
  alerts: ["Value Alert"],
  setUser: (user) => set({ user }),
  setPortfolio: (portfolio) => set({ portfolio }),
  setLiveGames: (liveGames) => set({ liveGames }),
  setAlerts: (alerts) => set({ alerts }),
}));
