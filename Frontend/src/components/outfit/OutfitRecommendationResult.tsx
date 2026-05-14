import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { OutfitRecommendationItem, OutfitRecommendationResponse } from "@/types/outfit";

interface OutfitRecommendationResultProps {
  recommendation: OutfitRecommendationResponse;
}

export const OutfitRecommendationResult = ({
  recommendation,
}: OutfitRecommendationResultProps) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 flex-wrap">
          {recommendation.outfit_name}
          {recommendation.harmony_type && (
            <Badge variant="secondary" className="text-xs font-normal shrink-0">
              {recommendation.harmony_type}
            </Badge>
          )}
        </CardTitle>
        {recommendation.confidence_score !== undefined && (
          <div className="space-y-1 pt-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Match confidence</span>
              <span className="font-medium text-foreground">{recommendation.confidence_score}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className={`h-full transition-all ${
                  recommendation.confidence_score >= 80
                    ? "bg-green-500"
                    : recommendation.confidence_score >= 60
                    ? "bg-amber-500"
                    : "bg-red-500"
                }`}
                style={{ width: `${recommendation.confidence_score}%` }}
              />
            </div>
          </div>
        )}
        <CardDescription>{recommendation.outfit_description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="overflow-x-auto pb-1">
          <div className="flex min-w-full gap-4">
            {recommendation.items.map((item) => (
              <RecommendationItemTile key={item.id} item={item} />
            ))}
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <section className="rounded-md border border-border/70 bg-muted/20 p-4">
            <h3 className="text-sm font-semibold text-foreground">Styling Tips</h3>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {recommendation.styling_tips.map((tip, index) => (
                <li key={`${tip}-${index}`}>{tip}</li>
              ))}
            </ul>
          </section>

          <section className="rounded-md border border-border/70 bg-muted/20 p-4">
            <h3 className="text-sm font-semibold text-foreground">Color Story</h3>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {recommendation.color_story || "No color story returned."}
            </p>
          </section>

          <section className="rounded-md border border-border/70 bg-muted/20 p-4">
            <h3 className="text-sm font-semibold text-foreground">Why It Fits You</h3>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {recommendation.why_it_fits_you}
            </p>
          </section>
        </div>
      </CardContent>
    </Card>
  );
};

const RecommendationItemTile = ({ item }: { item: OutfitRecommendationItem }) => {
  const [imageFailed, setImageFailed] = useState(false);
  const colorSwatch = item.color_hex || item.color || "#9CA3AF";
  const colorLabel = item.color_label || item.color || "Unknown color";
  const imageSrc = item.segmented_image_path || item.image_path || item.image_url;

  return (
    <div className="w-44 shrink-0 overflow-hidden rounded-md border border-border/70 bg-background">
      <div className="relative aspect-square bg-muted">
        {!imageFailed && imageSrc ? (
          <img
            src={imageSrc}
            alt={item.name}
            className="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center px-3 text-center text-xs text-muted-foreground">
            Image not available
          </div>
        )}
        {item.category && (
          <div className="absolute bottom-2 left-2">
            <Badge variant="secondary" className="text-xs">
              {item.category}
            </Badge>
          </div>
        )}
      </div>
      <div className="space-y-2 p-3">
        <h4 className="truncate text-sm font-semibold text-foreground">{item.name}</h4>
        <div className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-full border border-border"
            style={{ backgroundColor: colorSwatch }}
            title={colorLabel}
          />
          <span className="truncate text-xs text-muted-foreground">{colorLabel}</span>
        </div>
      </div>
    </div>
  );
};
