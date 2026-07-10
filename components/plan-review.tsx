"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { PageSectionManager } from "@/components/page-section-manager";
import { SitePlan } from "@/types/generation";

interface PlanReviewProps {
  plan: SitePlan;
  busy?: boolean;
  onApprove: (plan: SitePlan) => void;
  onRevise: (feedback: string) => void;
}

export function PlanReview({ plan, busy, onApprove, onRevise }: PlanReviewProps) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");

  return (
    <div className="space-y-5">
      <PageSectionManager plan={plan} busy={busy} onSubmit={onApprove} />

      <Card className="p-4">
        {!showFeedback ? (
          <button
            type="button"
            onClick={() => setShowFeedback(true)}
            disabled={busy}
            className="text-sm text-muted-foreground underline underline-offset-2 hover:text-foreground disabled:cursor-not-allowed disabled:opacity-50"
          >
            Not the right starting point? Ask the AI to re-plan the pages instead.
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              This replaces your page and section choices above with a fresh AI-generated plan.
            </p>
            <Textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="e.g. Combine the FAQ page into Home, and add a Careers page"
              rows={3}
              disabled={busy}
            />
            <div className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  onRevise(feedback);
                  setShowFeedback(false);
                  setFeedback("");
                }}
                disabled={busy || !feedback.trim()}
              >
                {busy ? "Revising…" : "Revise with AI"}
              </Button>
              <Button variant="ghost" onClick={() => setShowFeedback(false)} disabled={busy}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
