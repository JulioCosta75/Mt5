import React from "react";
import { render } from "@testing-library/react";
import RevolutionView from "./Revolution";
import { api } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  api: {
    knowledgeEaProfiles: jest.fn(),
    knowledgeCorrelation: jest.fn(),
  },
}));

const EMPTY = {
  profiles: [],
  counts: { under_review: 0, candidates: 0, validated: 0, graveyard: 0 },
};

const TWO_EAS = {
  account_id: "london-scalper",
  ea_key: "london-scalper",
  counts: { under_review: 1, candidates: 0, validated: 1, graveyard: 1 },
  profiles: [
    {
      ea_key: "london-scalper",
      name: "London Scalper",
      version: "1.0.0",
      purpose: "Fade the London open spread.",
      status: "active",
      permitted_symbols: ["XAUUSD"],
      permitted_sessions: ["London"],
      records: [
        {
          knowledge_record_id: "k1",
          validation_state: "knowledge",
          statement: "Spread filter reduces London open losses",
          is_stale: false,
        },
        {
          knowledge_record_id: "r1",
          validation_state: "evidence_under_review",
          statement: "NY overlap still under review",
        },
        {
          knowledge_record_id: "g1",
          validation_state: "invalidated_conclusion",
          statement: "London open always profitable",
          decided_by: "reviewer@forge",
          justification: "Contradictory evidence on NY session.",
        },
      ],
    },
    {
      ea_key: "ny-scalper",
      name: "NY Scalper",
      version: "2.1.0",
      purpose: "NY session mean reversion.",
      status: "testing",
      permitted_symbols: ["EURUSD"],
      permitted_sessions: ["NewYork"],
      records: [
        {
          knowledge_record_id: "p1",
          validation_state: "repeated_pattern",
          statement: "Thin liquidity after 21:00 UTC",
        },
      ],
    },
  ],
};

beforeEach(() => {
  api.knowledgeEaProfiles.mockReset();
  api.knowledgeCorrelation.mockReset();
  api.knowledgeEaProfiles.mockResolvedValue(EMPTY);
});

test("Revolution page has no action buttons", () => {
  const { container } = render(
    <RevolutionView
      accounts={[{ id: "ACC-001", login: 1 }]}
      selectedId="ACC-001"
      onSelect={() => {}}
    />
  );
  expect(container.querySelector("[data-testid='revolution-page']")).not.toBeNull();
  expect(container.querySelectorAll("button")).toHaveLength(0);
});

test("dossier grouping renders one card per EA and no action elements", async () => {
  api.knowledgeEaProfiles.mockResolvedValue(TWO_EAS);
  const { container, findAllByTestId, getAllByTestId } = render(
    <RevolutionView
      accounts={[{ id: "london-scalper", login: 1 }]}
      selectedId="london-scalper"
      onSelect={() => {}}
    />
  );
  const cards = await findAllByTestId("revolution-dossier");
  expect(cards).toHaveLength(2);
  expect(container.textContent).toMatch(/London Scalper/);
  expect(container.textContent).toMatch(/NY Scalper/);
  expect(container.textContent).toMatch(/Spread filter reduces London open losses/);
  expect(container.textContent).toMatch(/Thin liquidity after 21:00 UTC/);
  expect(cards[0].querySelector("[data-testid='revolution-graveyard']")).not.toBeNull();
  expect(cards[0].textContent).toMatch(/London open always profitable/);
  expect(getAllByTestId("revolution-pipeline")).toHaveLength(2);
  expect(container.querySelectorAll("button")).toHaveLength(0);
  expect(container.querySelector("[data-testid='revolution-summary']").textContent).toMatch(
    /Memory — what survived validation/
  );
});
