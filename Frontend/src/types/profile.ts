export type ModestyPreference = "Relaxed" | "Balanced" | "Modest";
export type EasternWesternPreference = "Eastern" | "Western" | "Both";
export type FitPreference = "Slim" | "Regular" | "Loose" | "Oversized";
export type LayeringPreference = "Avoid layers" | "Light layers" | "Like layers";
export type AccessoriesPreference =
  | "No accessories"
  | "Minimal accessories"
  | "Statement accessories";

export interface UserProfile {
  id: number;
  user_id: number;
  usual_contexts: string[];
  usual_context_other?: string | null;
  style_text?: string | null;
  formality_level?: number | null;
  comfort_style_level?: number | null;
  modesty_preference?: ModestyPreference | string | null;
  preferred_styles: string[];
  preferred_colors: string[];
  disliked_colors: string[];
  preferred_occasions: string[];
  eastern_western_preference?: EasternWesternPreference | string | null;
  clothing_avoid_text?: string | null;
  fit_preference?: FitPreference | string | null;
  layering_preference?: LayeringPreference | string | null;
  accessories_preference?: AccessoriesPreference | string | null;
  profile_completed: boolean;
  completed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export type ProfileUpdatePayload = Partial<
  Pick<
    UserProfile,
    | "usual_contexts"
    | "usual_context_other"
    | "style_text"
    | "formality_level"
    | "comfort_style_level"
    | "modesty_preference"
    | "preferred_styles"
    | "preferred_colors"
    | "disliked_colors"
    | "preferred_occasions"
    | "eastern_western_preference"
    | "clothing_avoid_text"
    | "fit_preference"
    | "layering_preference"
    | "accessories_preference"
  >
>;

export interface ProfileCompletionStatus {
  profile_completed: boolean;
  missing_fields: string[];
}
