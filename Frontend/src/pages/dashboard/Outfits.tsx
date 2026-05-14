import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/common/EmptyState";
import { outfitApi } from "@/lib/api/outfit";
import type { SavedOutfitResponse } from "@/types/outfit";
import { toast } from "sonner";

const Outfits = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: savedOutfits = [], isLoading } = useQuery({
    queryKey: ["savedOutfits"],
    queryFn: () => outfitApi.getSavedOutfits(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => outfitApi.deleteSavedOutfit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["savedOutfits"] });
      toast.success("Outfit removed");
    },
    onError: () => toast.error("Failed to remove outfit"),
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-foreground">Saved Outfits</h1>
          <p className="text-muted-foreground mt-2">
            Your saved outfit recommendations.
          </p>
        </div>
        <Button onClick={() => navigate("/dashboard/recommend")}>
          <Sparkles className="h-4 w-4 mr-2" />
          Generate New Look
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-6 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  {[0, 1, 2].map((j) => (
                    <Skeleton key={j} className="h-16 w-16 rounded-md" />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : savedOutfits.length === 0 ? (
        <EmptyState
          title="No saved outfits yet"
          description="Generate an outfit recommendation and save it to build your lookbook."
          icon={<Sparkles className="h-8 w-8" />}
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {savedOutfits.map((outfit) => (
            <SavedOutfitCard
              key={outfit.id}
              outfit={outfit}
              onDelete={() => deleteMutation.mutate(outfit.id)}
              isDeleting={deleteMutation.isPending && deleteMutation.variables === outfit.id}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface SavedOutfitCardProps {
  outfit: SavedOutfitResponse;
  onDelete: () => void;
  isDeleting: boolean;
}

const SavedOutfitCard = ({ outfit, onDelete, isDeleting }: SavedOutfitCardProps) => {
  const date = new Date(outfit.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  return (
    <Card className="flex flex-col">
      <CardHeader>
        <CardTitle className="text-base">{outfit.outfit_name}</CardTitle>
        <CardDescription className="line-clamp-2">{outfit.outfit_description}</CardDescription>
        {outfit.context_occasion && (
          <p className="text-xs text-muted-foreground">Occasion: {outfit.context_occasion}</p>
        )}
        <p className="text-xs text-muted-foreground">{date}</p>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        {outfit.items.length > 0 && (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {outfit.items.map((item) => (
              <SavedItemThumbnail key={item.id} src={item.image_url} alt={item.name} />
            ))}
          </div>
        )}
        <Button
          variant="outline"
          size="sm"
          className="mt-auto w-full text-destructive hover:text-destructive"
          onClick={onDelete}
          disabled={isDeleting}
        >
          <Trash2 className="mr-1.5 h-3.5 w-3.5" />
          {isDeleting ? "Removing..." : "Delete"}
        </Button>
      </CardContent>
    </Card>
  );
};

const SavedItemThumbnail = ({ src, alt }: { src: string; alt: string }) => {
  const [failed, setFailed] = useState(false);

  return (
    <div className="h-16 w-16 shrink-0 overflow-hidden rounded border border-border bg-muted">
      {!failed && src ? (
        <img
          src={src}
          alt={alt}
          className="h-full w-full object-cover"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center px-1 text-center text-[10px] text-muted-foreground">
          {alt}
        </div>
      )}
    </div>
  );
};

export default Outfits;
