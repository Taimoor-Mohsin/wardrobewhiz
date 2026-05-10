import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { StyleProfileForm } from "@/components/style/StyleProfileForm";
import { useAuth } from "@/hooks/use-auth";
import { profileKeys, useProfile } from "@/hooks/useProfile";

const Profile = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { profile, completion, isLoading } = useProfile();
  const [isEditOpen, setIsEditOpen] = useState(false);

  const completionPercent = completion?.completion_percentage ?? (profile?.profile_completed ? 100 : 0);

  if (isLoading) {
    return (
      <Card className="shadow-card">
        <CardContent className="py-10 text-center text-sm text-muted-foreground">
          Loading profile...
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Profile</h1>
          <p className="mt-2 text-muted-foreground">
            Review your account, style profile, preferences, and fit details.
          </p>
        </div>
        <Button onClick={() => setIsEditOpen(true)}>
          Edit Profile
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Profile overview</CardTitle>
            <CardDescription>Your signed-in WardrobeWiz account.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-xs uppercase text-muted-foreground">Name</p>
              <p className="font-medium text-foreground">{user?.name || "Not set"}</p>
            </div>
            <div>
              <p className="text-xs uppercase text-muted-foreground">Email</p>
              <p className="font-medium text-foreground">{user?.email || "Not set"}</p>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Profile completion</CardTitle>
            <CardDescription>Required before recommendations become available.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Badge variant={profile?.profile_completed ? "default" : "outline"}>
                {profile?.profile_completed ? "Complete" : "Incomplete"}
              </Badge>
              <span className="text-sm text-muted-foreground">{completionPercent}%</span>
            </div>
            <div className="h-2 rounded-full bg-muted">
              <div
                className="h-2 rounded-full bg-primary transition-all"
                style={{ width: `${completionPercent}%` }}
              />
            </div>
            {!profile?.profile_completed && (
              <p className="text-sm text-muted-foreground">
                Complete the style profile form to unlock the main dashboard.
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Measurements</CardTitle>
            <CardDescription>Fit details used for better sizing and outfit balance.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            <MeasurementTile label="Height" value={profile?.height} />
            <MeasurementTile label="Weight" value={profile?.weight} />
            <MeasurementTile label="Collar" value={profile?.collar} />
            <MeasurementTile label="Chest" value={profile?.chest} />
            <MeasurementTile label="Shoulder" value={profile?.shoulder} />
            <MeasurementTile label="Sleeve" value={profile?.sleeve_length} />
            <MeasurementTile label="Waist" value={profile?.waist} />
            <MeasurementTile label="Inseam" value={profile?.inseam} />
            <MeasurementTile label="Shoe size" value={profile?.shoe_size} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Style summary</CardTitle>
            <CardDescription>Your questionnaire responses at a glance.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <SummaryRow label="Usually dresses for" value={profile?.usual_contexts?.join(", ")} />
            <SummaryRow label="Everyday style" value={profile?.style_text} />
            <SummaryRow
              label="Formality"
              value={formatFormality(profile?.formality_level)}
            />
            <SummaryRow
              label="Comfort vs style"
              value={formatComfortStyle(profile?.comfort_style_level)}
            />
            <SummaryRow label="Eastern/Western" value={profile?.eastern_western_preference} />
            <SummaryRow label="Modesty" value={profile?.modesty_preference} />
            <SummaryRow label="Avoids" value={profile?.clothing_avoid_text} />
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Preferences</CardTitle>
            <CardDescription>Style, color, fit, layers, and accessories.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ColorSummary label="Preferred colors" colors={profile?.preferred_colors || []} />
            <ColorSummary label="Disliked colors" colors={profile?.disliked_colors || []} />
            <SummaryRow label="Aesthetics" value={profile?.preferred_styles?.join(", ")} />
            <SummaryRow label="Fit" value={profile?.fit_preference} />
            <SummaryRow label="Layering" value={profile?.layering_preference} />
            <SummaryRow label="Accessories" value={profile?.accessories_preference} />
          </CardContent>
        </Card>
      </div>

      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-h-[90vh] max-w-5xl overflow-hidden p-0">
          <DialogHeader className="px-6 pt-6">
            <DialogTitle>Edit Style Profile</DialogTitle>
            <DialogDescription>
              Update the preferences WardrobeWiz uses to personalize outfit recommendations.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[calc(90vh-96px)] overflow-y-auto px-6 pb-6">
            <StyleProfileForm
              mode="settings"
              onCompleted={() => {
                setIsEditOpen(false);
                void queryClient.invalidateQueries({ queryKey: profileKeys.all });
              }}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

const SummaryRow = ({ label, value }: { label: string; value?: string | null }) => (
  <div>
    <p className="text-xs uppercase text-muted-foreground">{label}</p>
    <p className="mt-1 text-sm font-medium text-foreground">{value || "Not set"}</p>
  </div>
);

const MeasurementTile = ({ label, value }: { label: string; value?: string | null }) => (
  <div className="rounded-md border border-border p-3">
    <p className="text-xs text-muted-foreground">{label}</p>
    <p className="font-medium text-foreground">{value || "Not set"}</p>
  </div>
);

const formatFormality = (value?: number | null) => {
  const labels: Record<number, string> = {
    1: "Very casual",
    2: "Casual leaning",
    3: "Balanced",
    4: "Formal leaning",
    5: "Very formal",
  };
  return value ? `${labels[value] || "Selected"} (${value}/5)` : null;
};

const formatComfortStyle = (value?: number | null) => {
  const labels: Record<number, string> = {
    1: "Comfort first",
    2: "Comfort leaning",
    3: "Balanced",
    4: "Style leaning",
    5: "Style first",
  };
  return value ? `${labels[value] || "Selected"} (${value}/5)` : null;
};

const ColorSummary = ({ label, colors }: { label: string; colors: string[] }) => (
  <div>
    <p className="text-xs uppercase text-muted-foreground">{label}</p>
    {colors.length ? (
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {colors.map((color) => (
          <div key={color} className="flex items-center gap-3 rounded-md border border-border p-3">
            <span
              className="h-12 w-12 shrink-0 rounded-md border border-border shadow-sm"
              style={{ backgroundColor: color }}
            />
            <div>
              <p className="text-xs text-muted-foreground">Color</p>
              <p className="text-sm font-semibold text-foreground">{color}</p>
            </div>
          </div>
        ))}
      </div>
    ) : (
      <p className="mt-1 text-sm font-medium text-foreground">Not set</p>
    )}
  </div>
);

export default Profile;
