import { useEffect, useMemo, useState } from "react";
import { HexColorPicker } from "react-colorful";
import { Check, X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { profileApi } from "@/lib/api/profile";
import { cn } from "@/lib/utils";
import { profileKeys, useProfile } from "@/hooks/useProfile";
import type { ProfileUpdatePayload, UserProfile } from "@/types/profile";
import { toast } from "sonner";

type StyleProfileDraft = {
  usual_contexts: string[];
  usual_context_other: string;
  style_text: string;
  formality_level: number | null;
  comfort_style_level: number | null;
  modesty_preference: string;
  eastern_western_preference: string;
  clothing_avoid_text: string;
  preferred_colors: string[];
  disliked_colors: string[];
  preferred_styles: string[];
  fit_preference: string;
  layering_preference: string;
  accessories_preference: string;
};

type StyleProfileFormProps = {
  mode?: "settings" | "onboarding";
  onCompleted?: () => void;
};

const usualContextOptions = [
  "University",
  "Work",
  "Casual hangouts",
  "Formal events",
  "Weddings",
  "Gym/Sports",
  "Other",
];

const aestheticOptions = [
  "Minimalist",
  "Classic",
  "Casual",
  "Formal",
  "Streetwear",
  "Modern",
  "Vintage",
  "Bohemian",
  "Eastern/Traditional",
  "Smart Casual",
];

const fitOptions = ["Slim", "Regular", "Loose", "Oversized"];
const modestyOptions = ["Relaxed", "Balanced", "Modest"];
const easternWesternOptions = ["Eastern", "Western", "Both"];
const layeringOptions = ["Avoid layers", "Light layers", "Like layers"];
const accessoriesOptions = ["No accessories", "Minimal accessories", "Statement accessories"];

const missingLabels: Record<string, string> = {
  usual_contexts: "Select at least one usual dressing context.",
  usual_context_other: "Describe the other dressing context.",
  style_text: "Describe your everyday style.",
  formality_level: "Choose your formality level.",
  comfort_style_level: "Choose your comfort vs style preference.",
  modesty_preference: "Choose your modesty preference.",
  eastern_western_preference: "Choose Eastern, Western, or Both.",
  preferred_colors: "Add at least one preferred color.",
  preferred_styles: "Select at least one style aesthetic.",
  fit_preference: "Choose a fit preference.",
  layering_preference: "Choose a layering preference.",
  accessories_preference: "Choose an accessories preference.",
};

const emptyDraft: StyleProfileDraft = {
  usual_contexts: [],
  usual_context_other: "",
  style_text: "",
  formality_level: null,
  comfort_style_level: null,
  modesty_preference: "",
  eastern_western_preference: "",
  clothing_avoid_text: "",
  preferred_colors: [],
  disliked_colors: [],
  preferred_styles: [],
  fit_preference: "",
  layering_preference: "",
  accessories_preference: "",
};

const profileToDraft = (profile?: UserProfile): StyleProfileDraft => {
  if (!profile) {
    return emptyDraft;
  }

  return {
    usual_contexts: profile.usual_contexts || [],
    usual_context_other: profile.usual_context_other || "",
    style_text: profile.style_text || "",
    formality_level: profile.formality_level ?? null,
    comfort_style_level: profile.comfort_style_level ?? null,
    modesty_preference: profile.modesty_preference || "",
    eastern_western_preference: profile.eastern_western_preference || "",
    clothing_avoid_text: profile.clothing_avoid_text || "",
    preferred_colors: profile.preferred_colors || [],
    disliked_colors: profile.disliked_colors || [],
    preferred_styles: profile.preferred_styles || [],
    fit_preference: profile.fit_preference || "",
    layering_preference: profile.layering_preference || "",
    accessories_preference: profile.accessories_preference || "",
  };
};

const getMissingFields = (draft: StyleProfileDraft) => {
  const missing: string[] = [];

  if (!draft.usual_contexts.length) missing.push("usual_contexts");
  if (draft.usual_contexts.includes("Other") && !draft.usual_context_other.trim()) {
    missing.push("usual_context_other");
  }
  if (!draft.style_text.trim()) missing.push("style_text");
  if (draft.formality_level === null) missing.push("formality_level");
  if (draft.comfort_style_level === null) missing.push("comfort_style_level");
  if (!draft.modesty_preference) missing.push("modesty_preference");
  if (!draft.eastern_western_preference) missing.push("eastern_western_preference");
  if (!draft.preferred_colors.length) missing.push("preferred_colors");
  if (!draft.preferred_styles.length) missing.push("preferred_styles");
  if (!draft.fit_preference) missing.push("fit_preference");
  if (!draft.layering_preference) missing.push("layering_preference");
  if (!draft.accessories_preference) missing.push("accessories_preference");

  return missing;
};

const draftToPayload = (draft: StyleProfileDraft): ProfileUpdatePayload => ({
  usual_contexts: draft.usual_contexts,
  usual_context_other: draft.usual_context_other.trim() || null,
  style_text: draft.style_text.trim() || null,
  formality_level: draft.formality_level,
  comfort_style_level: draft.comfort_style_level,
  modesty_preference: draft.modesty_preference || null,
  eastern_western_preference: draft.eastern_western_preference || null,
  clothing_avoid_text: draft.clothing_avoid_text.trim() || null,
  preferred_colors: draft.preferred_colors,
  disliked_colors: draft.disliked_colors,
  preferred_styles: draft.preferred_styles,
  fit_preference: draft.fit_preference || null,
  layering_preference: draft.layering_preference || null,
  accessories_preference: draft.accessories_preference || null,
});

export const StyleProfileForm = ({ mode = "settings", onCompleted }: StyleProfileFormProps) => {
  const queryClient = useQueryClient();
  const { profile, isLoading, isUpdating, updateProfile } = useProfile();
  const [draft, setDraft] = useState<StyleProfileDraft>(emptyDraft);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [preferredColor, setPreferredColor] = useState("#1F2937");
  const [dislikedColor, setDislikedColor] = useState("#DC2626");

  useEffect(() => {
    setDraft(profileToDraft(profile));
  }, [profile]);

  const completionPercent = useMemo(() => {
    const total = Object.keys(missingLabels).length;
    return Math.round(((total - getMissingFields(draft).length) / total) * 100);
  }, [draft]);

  const updateDraft = <Key extends keyof StyleProfileDraft>(
    key: Key,
    value: StyleProfileDraft[Key],
  ) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const toggleArrayValue = (key: "usual_contexts" | "preferred_styles", value: string) => {
    setDraft((prev) => {
      const currentValues = prev[key];
      const nextValues = currentValues.includes(value)
        ? currentValues.filter((item) => item !== value)
        : [...currentValues, value];
      return { ...prev, [key]: nextValues };
    });
  };

  const addColor = (key: "preferred_colors" | "disliked_colors", color: string) => {
    setDraft((prev) => ({
      ...prev,
      [key]: prev[key].includes(color) ? prev[key] : [...prev[key], color],
    }));
  };

  const removeColor = (key: "preferred_colors" | "disliked_colors", color: string) => {
    setDraft((prev) => ({
      ...prev,
      [key]: prev[key].filter((item) => item !== color),
    }));
  };

  const handleSave = async () => {
    const updatedProfile = await updateProfile(draftToPayload(draft));
    const completion = await profileApi.getCompletionStatus();
    queryClient.setQueryData(profileKeys.completion(), completion);

    if (updatedProfile.profile_completed) {
      setMissingFields([]);
      toast.success(mode === "onboarding" ? "Profile completed" : "Style profile saved");
      onCompleted?.();
      return;
    }

    const missing = completion.missing_fields.length
      ? completion.missing_fields
      : getMissingFields(draft);
    setMissingFields(missing);
    toast.error("Complete the highlighted profile details before continuing.");
  };

  if (isLoading) {
    return (
      <Card className="shadow-card">
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Loading style profile...
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-card">
      <CardHeader>
        <CardTitle>Style Profiling</CardTitle>
        <CardDescription>
          Complete these details so WardrobeWiz can personalize wardrobe and outfit recommendations.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="rounded-md border border-border bg-muted/30 p-4">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-medium text-foreground">Profile completion</p>
            <p className="text-sm text-muted-foreground">{completionPercent}%</p>
          </div>
          <div className="mt-3 h-2 rounded-full bg-background">
            <div
              className="h-2 rounded-full bg-primary transition-all"
              style={{ width: `${completionPercent}%` }}
            />
          </div>
        </div>

        {missingFields.length > 0 && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 p-4">
            <p className="text-sm font-medium text-destructive">Still needed</p>
            <ul className="mt-2 space-y-1 text-sm text-destructive">
              {missingFields.map((field) => (
                <li key={field}>{missingLabels[field] || field}</li>
              ))}
            </ul>
          </div>
        )}

        <Tabs defaultValue="questionnaire" className="w-full">
          <TabsList>
            <TabsTrigger value="questionnaire">Questionnaire</TabsTrigger>
            <TabsTrigger value="preferences">Preferences</TabsTrigger>
          </TabsList>

          <TabsContent value="questionnaire" className="space-y-6 pt-4">
            <div className="space-y-3">
              <Label>What do you usually dress for?</Label>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {usualContextOptions.map((option) => (
                  <label
                    key={option}
                    className="flex cursor-pointer items-center gap-3 rounded-md border border-border p-3 text-sm hover:bg-muted/60"
                  >
                    <Checkbox
                      checked={draft.usual_contexts.includes(option)}
                      onCheckedChange={() => toggleArrayValue("usual_contexts", option)}
                    />
                    {option}
                  </label>
                ))}
              </div>
              {draft.usual_contexts.includes("Other") && (
                <Input
                  placeholder="Tell us what else you dress for"
                  value={draft.usual_context_other}
                  onChange={(event) => updateDraft("usual_context_other", event.target.value)}
                />
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="style_text">How would you describe your everyday style?</Label>
              <Textarea
                id="style_text"
                placeholder="E.g. relaxed smart casual, clean colors, comfortable shoes"
                value={draft.style_text}
                onChange={(event) => updateDraft("style_text", event.target.value)}
              />
            </div>

            <ScaleField
              label="How formal do you usually prefer your outfits?"
              leftLabel="Very casual"
              rightLabel="Very formal"
              value={draft.formality_level}
              onChange={(value) => updateDraft("formality_level", value)}
            />

            <ScaleField
              label="Comfort vs style?"
              leftLabel="Comfort first"
              rightLabel="Style first"
              value={draft.comfort_style_level}
              onChange={(value) => updateDraft("comfort_style_level", value)}
            />

            <ChoiceGroup
              label="How modest do you prefer your outfits?"
              options={modestyOptions}
              value={draft.modesty_preference}
              onChange={(value) => updateDraft("modesty_preference", value)}
            />

            <ChoiceGroup
              label="Do you prefer Eastern, Western, or both?"
              options={easternWesternOptions}
              value={draft.eastern_western_preference}
              onChange={(value) => updateDraft("eastern_western_preference", value)}
            />

            <div className="space-y-2">
              <Label htmlFor="clothing_avoid_text">Any clothing you avoid?</Label>
              <Textarea
                id="clothing_avoid_text"
                placeholder="E.g. avoid wool in daytime, tight collars, neon colors"
                value={draft.clothing_avoid_text}
                onChange={(event) => updateDraft("clothing_avoid_text", event.target.value)}
              />
            </div>
          </TabsContent>

          <TabsContent value="preferences" className="space-y-6 pt-4">
            <ColorField
              label="Preferred colors"
              colors={draft.preferred_colors}
              pickerColor={preferredColor}
              onPickerColorChange={setPreferredColor}
              onAdd={() => addColor("preferred_colors", preferredColor)}
              onRemove={(color) => removeColor("preferred_colors", color)}
            />

            <ColorField
              label="Disliked colors"
              colors={draft.disliked_colors}
              pickerColor={dislikedColor}
              onPickerColorChange={setDislikedColor}
              onAdd={() => addColor("disliked_colors", dislikedColor)}
              onRemove={(color) => removeColor("disliked_colors", color)}
            />

            <CardGrid
              label="Style aesthetics"
              options={aestheticOptions}
              selectedValues={draft.preferred_styles}
              multi
              onToggle={(value) => toggleArrayValue("preferred_styles", value)}
            />

            <CardGrid
              label="Fit preference"
              options={fitOptions}
              selectedValues={draft.fit_preference ? [draft.fit_preference] : []}
              onToggle={(value) => updateDraft("fit_preference", value)}
            />

            <ChoiceGroup
              label="Layering preference"
              options={layeringOptions}
              value={draft.layering_preference}
              onChange={(value) => updateDraft("layering_preference", value)}
            />

            <ChoiceGroup
              label="Accessories preference"
              options={accessoriesOptions}
              value={draft.accessories_preference}
              onChange={(value) => updateDraft("accessories_preference", value)}
            />
          </TabsContent>
        </Tabs>

        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={isUpdating}>
            {isUpdating ? "Saving..." : mode === "onboarding" ? "Save & Continue" : "Save Profile"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

const ScaleField = ({
  label,
  leftLabel,
  rightLabel,
  value,
  onChange,
}: {
  label: string;
  leftLabel: string;
  rightLabel: string;
  value: number | null;
  onChange: (value: number) => void;
}) => (
  <div className="space-y-3">
    <Label>{label}</Label>
    <Slider
      min={1}
      max={5}
      step={1}
      value={[value ?? 3]}
      onValueChange={([nextValue]) => onChange(nextValue)}
    />
    <div className="flex justify-between text-xs text-muted-foreground">
      <span>{leftLabel}</span>
      <span>{rightLabel}</span>
    </div>
  </div>
);

const ChoiceGroup = ({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) => (
  <div className="space-y-3">
    <Label>{label}</Label>
    <div className="grid gap-2 sm:grid-cols-3">
      {options.map((option) => (
        <Button
          key={option}
          type="button"
          variant={value === option ? "default" : "outline"}
          className="h-auto min-h-11 whitespace-normal"
          onClick={() => onChange(option)}
        >
          {option}
        </Button>
      ))}
    </div>
  </div>
);

const ColorField = ({
  label,
  colors,
  pickerColor,
  onPickerColorChange,
  onAdd,
  onRemove,
}: {
  label: string;
  colors: string[];
  pickerColor: string;
  onPickerColorChange: (color: string) => void;
  onAdd: () => void;
  onRemove: (color: string) => void;
}) => (
  <div className="space-y-3">
    <Label>{label}</Label>
    <div className="flex flex-wrap gap-2">
      {colors.map((color) => (
        <Badge key={color} variant="secondary" className="gap-2">
          <span className="h-3 w-3 rounded-full border" style={{ backgroundColor: color }} />
          {color}
          <button type="button" onClick={() => onRemove(color)} aria-label={`Remove ${color}`}>
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
      <Popover>
        <PopoverTrigger asChild>
          <Button type="button" variant="outline" size="sm">
            Add color
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto space-y-3 p-3">
          <HexColorPicker color={pickerColor} onChange={onPickerColorChange} />
          <Button type="button" size="sm" className="w-full" onClick={onAdd}>
            Add {pickerColor}
          </Button>
        </PopoverContent>
      </Popover>
    </div>
  </div>
);

const CardGrid = ({
  label,
  options,
  selectedValues,
  onToggle,
  multi = false,
}: {
  label: string;
  options: string[];
  selectedValues: string[];
  onToggle: (value: string) => void;
  multi?: boolean;
}) => (
  <div className="space-y-3">
    <Label>{label}</Label>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {options.map((option) => {
        const selected = selectedValues.includes(option);
        return (
          <button
            key={option}
            type="button"
            className={cn(
              "min-h-28 rounded-md border border-border bg-background p-3 text-left transition hover:border-primary/50",
              selected && "border-primary bg-primary/10",
            )}
            onClick={() => onToggle(option)}
          >
            <div className="mb-3 flex h-12 items-center justify-center rounded-md bg-muted text-sm font-semibold text-muted-foreground">
              {option
                .split(/[ /]/)
                .map((part) => part.charAt(0))
                .join("")
                .slice(0, 3)}
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-foreground">{option}</span>
              {selected && <Check className="h-4 w-4 text-primary" />}
            </div>
            {multi && <p className="mt-1 text-xs text-muted-foreground">Tap to toggle</p>}
          </button>
        );
      })}
    </div>
  </div>
);
