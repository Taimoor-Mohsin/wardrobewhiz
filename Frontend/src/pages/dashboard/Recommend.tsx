import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { AlertCircle, Bookmark, BookmarkCheck, Loader2, Shuffle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { ContextInputForm } from "@/components/outfit/ContextInputForm";
import { OutfitFeedbackButtons } from "@/components/outfit/OutfitFeedbackButtons";
import { OutfitRecommendationResult } from "@/components/outfit/OutfitRecommendationResult";
import { outfitApi } from "@/lib/api/outfit";
import type { OutfitRecommendationRequest } from "@/types/outfit";
import { toast } from "sonner";

const initialContext: OutfitRecommendationRequest = {
  occasion: "",
  weather: "",
  temperature_c: 26,
  mood: "",
  dress_code: "",
  notes: "",
};

const Recommend = () => {
  const [context, setContext] = useState<OutfitRecommendationRequest>(initialContext);
  const [occasionError, setOccasionError] = useState("");
  const [lastAction, setLastAction] = useState<"generate" | "surprise" | null>(null);
  const [isSaved, setIsSaved] = useState(false);
  const [savedOutfitId, setSavedOutfitId] = useState<number | null>(null);

  const recommendationMutation = useMutation({
    mutationFn: (request: OutfitRecommendationRequest) => outfitApi.recommendOutfit(request),
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const surpriseMutation = useMutation({
    mutationFn: () => outfitApi.surpriseMe(),
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const recommendation = recommendationMutation.data;
  const isGenerating = recommendationMutation.isPending;
  const errorMessage = recommendationMutation.error
    ? getErrorMessage(recommendationMutation.error)
    : "";

  const isSurprising = surpriseMutation.isPending;
  const isAnyPending = isGenerating || isSurprising;

  const displayRecommendation =
    lastAction === "surprise" ? surpriseMutation.data : recommendation;
  const displayError =
    lastAction === "surprise"
      ? surpriseMutation.error
        ? getErrorMessage(surpriseMutation.error)
        : ""
      : errorMessage;

  const saveMutation = useMutation({
    mutationFn: () =>
      outfitApi.saveOutfit(displayRecommendation!, context.occasion || null),
    onSuccess: (data: { id: number }) => {
      setIsSaved(true);
      setSavedOutfitId(data.id);
      toast.success("Outfit saved to your lookbook!");
    },
    onError: (error) => toast.error(getErrorMessage(error)),
  });

  const handleContextChange = (updated: OutfitRecommendationRequest) => {
    setContext(updated);
    if (updated.occasion.trim()) setOccasionError("");
  };

  const handleGenerate = () => {
    if (!context.occasion.trim()) {
      setOccasionError("Occasion is required.");
      return;
    }
    setOccasionError("");

    if (!context.occasion.trim() && !context.location?.trim() && !context.weather.trim()) {
      toast.error("Please provide at least occasion, location, or weather information");
      return;
    }

    setLastAction("generate");
    setIsSaved(false);
    setSavedOutfitId(null);
    recommendationMutation.mutate({
      ...context,
      notes: context.notes?.trim() || null,
    });
  };

  const handleSurprise = () => {
    setLastAction("surprise");
    setIsSaved(false);
    setSavedOutfitId(null);
    surpriseMutation.mutate();
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Outfit Recommendations</h1>
        <p className="text-muted-foreground mt-2">
          Describe your day and context, and WardrobeWiz will suggest the perfect outfit.
        </p>
      </div>

      <ContextInputForm context={context} onChange={handleContextChange} occasionError={occasionError} />

      <Card>
        <CardHeader>
          <CardTitle>What WardrobeWiz Considers</CardTitle>
          <CardDescription>
            The backend uses your closet, style profile, context, and weather details before asking Groq.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>Your wardrobe items and their usage history</li>
            <li>Weather conditions and temperature</li>
            <li>Occasion and dress code requirements</li>
            <li>Your style preferences and color palette</li>
            <li>Item structure checks before returning a recommendation</li>
          </ul>
        </CardContent>
      </Card>

      <div className="flex flex-col sm:flex-row gap-3 justify-center">
        <Button
          onClick={handleGenerate}
          disabled={isAnyPending}
          size="lg"
          className="w-full sm:w-auto"
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-4 w-4" />
              Generate Outfit
            </>
          )}
        </Button>

        <Button
          onClick={handleSurprise}
          disabled={isAnyPending}
          variant="outline"
          size="lg"
          className="w-full sm:w-auto"
        >
          {isSurprising ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Surprising...
            </>
          ) : (
            <>
              <Shuffle className="mr-2 h-4 w-4" />
              Surprise Me
            </>
          )}
        </Button>
      </div>

      {displayError && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Recommendation failed
            </CardTitle>
            <CardDescription>{displayError}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              onClick={lastAction === "surprise" ? handleSurprise : handleGenerate}
              disabled={isAnyPending}
            >
              Try again
            </Button>
          </CardContent>
        </Card>
      )}

      {isAnyPending && <RecommendationSkeleton />}

      {!displayRecommendation && !displayError && !isAnyPending && (
        <EmptyState
          title="No recommendation yet"
          description="Fill in the context above to request an outfit recommendation from your wardrobe."
          icon={<Sparkles className="h-8 w-8" />}
        />
      )}

      {displayRecommendation && !isAnyPending && (
        <>
          <OutfitRecommendationResult recommendation={displayRecommendation} />
          <div className="flex flex-col items-center gap-4">
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={isSaved || saveMutation.isPending}
              variant="outline"
            >
              {saveMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : isSaved ? (
                <>
                  <BookmarkCheck className="mr-2 h-4 w-4" />
                  Saved
                </>
              ) : (
                <>
                  <Bookmark className="mr-2 h-4 w-4" />
                  Save Outfit
                </>
              )}
            </Button>
            {savedOutfitId !== null && (
              <OutfitFeedbackButtons outfitId={savedOutfitId} />
            )}
          </div>
        </>
      )}
    </div>
  );
};

const getErrorMessage = (error: unknown) => {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return "Unable to generate an outfit recommendation.";
};

const RecommendationSkeleton = () => (
  <Card>
    <CardHeader>
      <Skeleton className="h-6 w-56" />
      <Skeleton className="h-4 w-full max-w-2xl" />
    </CardHeader>
    <CardContent className="space-y-6">
      <div className="flex gap-4 overflow-hidden">
        {[0, 1, 2, 3].map((item) => (
          <div key={item} className="w-44 shrink-0 space-y-3">
            <Skeleton className="aspect-square w-full rounded-md" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <div key={item} className="rounded-md border border-border/70 p-4">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="mt-4 h-3 w-full" />
            <Skeleton className="mt-2 h-3 w-5/6" />
            <Skeleton className="mt-2 h-3 w-2/3" />
          </div>
        ))}
      </div>
    </CardContent>
  </Card>
);

export default Recommend;
