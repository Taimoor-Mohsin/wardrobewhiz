import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { AlertCircle, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { ContextInputForm } from "@/components/outfit/ContextInputForm";
import { OutfitRecommendationResult } from "@/components/outfit/OutfitRecommendationResult";
import { outfitApi } from "@/lib/api/outfit";
import type { OutfitRecommendationRequest } from "@/types/outfit";
import { toast } from "sonner";

const initialContext: OutfitRecommendationRequest = {
  occasion: "",
  location: "",
  weather: "",
  temperature_c: 26,
  mood: "",
  dress_code: "",
  notes: "",
};

const Recommend = () => {
  const [context, setContext] = useState<OutfitRecommendationRequest>(initialContext);

  const recommendationMutation = useMutation({
    mutationFn: (request: OutfitRecommendationRequest) => outfitApi.recommendOutfit(request),
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const recommendation = recommendationMutation.data;
  const isGenerating = recommendationMutation.isPending;
  const errorMessage = recommendationMutation.error
    ? getErrorMessage(recommendationMutation.error)
    : "";

  const handleGenerate = () => {
    if (!context.occasion.trim() && !context.location.trim() && !context.weather.trim()) {
      toast.error("Please provide at least occasion, location, or weather information");
      return;
    }

    recommendationMutation.mutate({
      ...context,
      notes: context.notes?.trim() || null,
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Outfit Recommendations</h1>
        <p className="text-muted-foreground mt-2">
          Describe your day and context, and WardrobeWiz will suggest the perfect outfit.
        </p>
      </div>

      <ContextInputForm context={context} onChange={setContext} />

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

      <div className="flex justify-center">
        <Button
          onClick={handleGenerate}
          disabled={isGenerating}
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
      </div>

      {errorMessage && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Recommendation failed
            </CardTitle>
            <CardDescription>{errorMessage}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={handleGenerate} disabled={isGenerating}>
              Try again
            </Button>
          </CardContent>
        </Card>
      )}

      {isGenerating && <RecommendationSkeleton />}

      {!recommendation && !errorMessage && !isGenerating && (
        <EmptyState
          title="No recommendation yet"
          description="Fill in the context above to request an outfit recommendation from your wardrobe."
          icon={<Sparkles className="h-8 w-8" />}
        />
      )}

      {recommendation && !isGenerating && (
        <OutfitRecommendationResult recommendation={recommendation} />
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
