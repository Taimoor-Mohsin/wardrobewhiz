import { useMemo, useState } from "react";
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

const completionFields = [
  "usual_contexts",
  "style_text",
  "formality_level",
  "comfort_style_level",
  "modesty_preference",
  "eastern_western_preference",
  "preferred_colors",
  "preferred_styles",
  "fit_preference",
  "layering_preference",
  "accessories_preference",
];

const Profile = () => {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { profile, completion, isLoading } = useProfile();
  const [isEditOpen, setIsEditOpen] = useState(false);

  const completionPercent = useMemo(() => {
    if (!completion) {
      return profile?.profile_completed ? 100 : 0;
    }
    const completed = completionFields.length - completion.missing_fields.length;
    return Math.max(0, Math.round((completed / completionFields.length) * 100));
  }, [completion, profile?.profile_completed]);

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
            <CardDescription>Fit details will live here in the next phase.</CardDescription>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-3 text-sm">
            {["Height", "Weight", "Waist", "Shoe size"].map((label) => (
              <div key={label} className="rounded-md border border-border p-3">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="font-medium text-foreground">Not set</p>
              </div>
            ))}
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

const ColorSummary = ({ label, colors }: { label: string; colors: string[] }) => (
  <div>
    <p className="text-xs uppercase text-muted-foreground">{label}</p>
    {colors.length ? (
      <div className="mt-2 flex flex-wrap gap-2">
        {colors.map((color) => (
          <span key={color} className="flex items-center gap-2 rounded-full border px-2 py-1 text-xs">
            <span className="h-3 w-3 rounded-full border" style={{ backgroundColor: color }} />
            {color}
          </span>
        ))}
      </div>
    ) : (
      <p className="mt-1 text-sm font-medium text-foreground">Not set</p>
    )}
  </div>
);

export default Profile;
