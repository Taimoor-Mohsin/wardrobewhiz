import { useMutation } from "@tanstack/react-query";
import { feedbackApi } from "@/lib/api/feedback";
import type { OutfitFeedbackRequest } from "@/types/outfit";
import { toast } from "sonner";

export const useFeedback = () => {
  const submitMutation = useMutation({
    mutationFn: (payload: OutfitFeedbackRequest) => feedbackApi.submitFeedback(payload),
    onSuccess: () => toast.success("Feedback submitted"),
    onError: () => toast.error("Failed to submit feedback"),
  });

  return {
    submitFeedback: submitMutation.mutate,
    isSubmitting: submitMutation.isPending,
  };
};
