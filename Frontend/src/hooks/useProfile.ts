import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { profileApi } from "@/lib/api/profile";
import type { ProfileCompletionStatus, ProfileUpdatePayload } from "@/types/profile";

export const profileKeys = {
  all: ["profile"] as const,
  current: () => [...profileKeys.all, "current"] as const,
  completion: () => [...profileKeys.all, "completion"] as const,
};

export const useProfile = () => {
  const queryClient = useQueryClient();

  const profileQuery = useQuery({
    queryKey: profileKeys.current(),
    queryFn: profileApi.getCurrentProfile,
  });

  const completionQuery = useQuery({
    queryKey: profileKeys.completion(),
    queryFn: profileApi.getCompletionStatus,
  });

  const updateProfileMutation = useMutation({
    mutationFn: (payload: ProfileUpdatePayload) => profileApi.updateCurrentProfile(payload),
    onSuccess: (profile) => {
      const previousCompletion = queryClient.getQueryData<ProfileCompletionStatus>(
        profileKeys.completion(),
      );
      queryClient.setQueryData(profileKeys.current(), profile);
      queryClient.setQueryData(profileKeys.completion(), {
        profile_completed: profile.profile_completed,
        missing_fields: profile.profile_completed ? [] : previousCompletion?.missing_fields ?? [],
      });
      void queryClient.invalidateQueries({ queryKey: profileKeys.all });
    },
  });

  return {
    profile: profileQuery.data,
    completion: completionQuery.data,
    isLoading: profileQuery.isLoading || completionQuery.isLoading,
    isError: profileQuery.isError || completionQuery.isError,
    updateProfile: updateProfileMutation.mutateAsync,
    isUpdating: updateProfileMutation.isPending,
  };
};

export const useProfileCompletion = () =>
  useQuery({
    queryKey: profileKeys.completion(),
    queryFn: profileApi.getCompletionStatus,
  });
