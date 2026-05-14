import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Loader2, ThumbsDown, ThumbsUp } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { feedbackApi } from "@/lib/api/feedback";
import { cn } from "@/lib/utils";

interface OutfitFeedbackButtonsProps {
  outfitId: number;
  className?: string;
}

export const OutfitFeedbackButtons = ({ outfitId, className }: OutfitFeedbackButtonsProps) => {
  const [selectedRating, setSelectedRating] = useState<1 | -1 | null>(null);

  const feedbackMutation = useMutation({
    mutationFn: (rating: 1 | -1) => feedbackApi.submitFeedback({ outfit_id: outfitId, rating }),
    onSuccess: () => toast.success("Feedback submitted"),
    onError: () => toast.error("Failed to submit feedback"),
  });

  const isDisabled = feedbackMutation.isSuccess || feedbackMutation.isPending;

  const handleRate = (rating: 1 | -1) => {
    if (isDisabled) return;
    setSelectedRating(rating);
    feedbackMutation.mutate(rating);
  };

  return (
    <div className={cn("flex gap-2", className)}>
      <Button
        variant={selectedRating === 1 && feedbackMutation.isSuccess ? "default" : "outline"}
        size="sm"
        disabled={isDisabled}
        onClick={() => handleRate(1)}
      >
        {feedbackMutation.isPending && selectedRating === 1 ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <ThumbsUp className="h-4 w-4 mr-2" />
        )}
        Like
      </Button>
      <Button
        variant={selectedRating === -1 && feedbackMutation.isSuccess ? "destructive" : "outline"}
        size="sm"
        disabled={isDisabled}
        onClick={() => handleRate(-1)}
      >
        {feedbackMutation.isPending && selectedRating === -1 ? (
          <Loader2 className="h-4 w-4 animate-spin mr-2" />
        ) : (
          <ThumbsDown className="h-4 w-4 mr-2" />
        )}
        Dislike
      </Button>
    </div>
  );
};
