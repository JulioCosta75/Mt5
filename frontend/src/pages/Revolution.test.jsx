import React from "react";
import { render } from "@testing-library/react";
import RevolutionView from "./Revolution";

jest.mock("@/lib/api", () => ({
  api: {
    knowledgeInsights: jest.fn().mockResolvedValue({
      insights: [],
      counts: { validated: 0, active_now: 0 },
    }),
    knowledgeGraveyard: jest.fn().mockResolvedValue({ entries: [], count: 0 }),
    knowledgeCorrelation: jest.fn(),
  },
}));

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
