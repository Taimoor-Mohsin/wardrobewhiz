import { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { OutfitRecommendationRequest } from "@/types/outfit";

interface ContextInputFormProps {
  context: OutfitRecommendationRequest;
  onChange: (context: OutfitRecommendationRequest) => void;
  occasionError?: string;
  className?: string;
}

export const ContextInputForm = ({
  context,
  onChange,
  occasionError,
  className,
}: ContextInputFormProps) => {
  const [showFilters, setShowFilters] = useState(false);

  const handleChange = (
    field: keyof OutfitRecommendationRequest,
    value: string | number | null,
  ) => {
    onChange({
      ...context,
      [field]: value,
    });
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Outfit Context</CardTitle>
        <CardDescription>
          Provide details about the occasion, weather, and your preferences
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="occasion">
            Occasion <span className="text-destructive">*</span>
          </Label>
          <Input
            id="occasion"
            placeholder="e.g., Board meeting, Casual dinner"
            value={context.occasion}
            onChange={(event) => handleChange("occasion", event.target.value)}
          />
          {occasionError && (
            <p className="text-sm text-destructive">{occasionError}</p>
          )}
        </div>

        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="px-0 text-muted-foreground hover:text-foreground"
          onClick={() => setShowFilters((prev) => !prev)}
        >
          {showFilters ? "Hide filters −" : "Add filters +"}
        </Button>

        {showFilters && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="weather">Weather</Label>
              <Input
                id="weather"
                placeholder="e.g., Sunny, Humid, Cold"
                value={context.weather}
                onChange={(event) => handleChange("weather", event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="temperature">Temperature (C)</Label>
              <Input
                id="temperature"
                type="number"
                placeholder="e.g., 26"
                value={context.temperature_c || ""}
                onChange={(event) => handleChange("temperature_c", Number(event.target.value) || 0)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="mood">Mood / Style</Label>
              <Input
                id="mood"
                placeholder="e.g., Professional, Casual, Playful"
                value={context.mood}
                onChange={(event) => handleChange("mood", event.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="dressCode">Dress Code</Label>
              <Input
                id="dressCode"
                placeholder="e.g., Business casual, Smart casual"
                value={context.dress_code}
                onChange={(event) => handleChange("dress_code", event.target.value)}
              />
            </div>
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="notes">Additional Notes</Label>
          <Textarea
            id="notes"
            placeholder="Any additional context or preferences..."
            value={context.notes || ""}
            onChange={(event) => handleChange("notes", event.target.value || null)}
            rows={3}
          />
        </div>
      </CardContent>
    </Card>
  );
};
