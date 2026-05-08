import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DialogFooter } from "@/components/ui/dialog";
import { MetadataForm } from "./MetadataForm";
import { wardrobeApi } from "@/lib/api/wardrobe";
import type { WardrobeItem, WardrobeItemMetadata } from "@/types/wardrobe";

interface WardrobeItemFormProps {
  item: WardrobeItem;
  flowLabel: string;
  saveLabel?: string;
  cancelLabel?: string;
  previewDetails?: ReactNode;
  onCancel?: () => void;
  onUpdated?: (item: WardrobeItem) => void | Promise<void>;
}

const getItemMetadata = (item: WardrobeItem): WardrobeItemMetadata => ({
  name: item.name,
  category: item.category,
  type: item.type,
  subcategory: item.subcategory,
  color: item.swatchColorHex || item.color,
  season: item.season,
  description: item.description,
  notes: item.notes,
  tags: item.tags,
});

export const WardrobeItemForm = ({
  item,
  flowLabel,
  saveLabel = "Save Changes",
  cancelLabel = "Cancel",
  previewDetails,
  onCancel,
  onUpdated,
}: WardrobeItemFormProps) => {
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState<WardrobeItemMetadata>(() => getItemMetadata(item));
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    const initialValues = getItemMetadata(item);
    setFormState(initialValues);
    console.log("[WardrobeItemForm] Initial values passed to form", {
      flowLabel,
      itemId: item.id,
      values: initialValues,
    });
  }, [flowLabel, item]);

  const handleSave = async () => {
    const payload = {
      name: formState.name,
      category: formState.category,
      subcategory: formState.subcategory,
      color: formState.color,
      season: formState.season,
      description: formState.description,
    };

    console.log("[WardrobeItemForm] Payload sent on save", {
      flowLabel,
      itemId: item.id,
      payload,
    });

    try {
      setIsSaving(true);
      const updatedItem = await wardrobeApi.updateWardrobeItem(item.id, payload);
      console.log("[WardrobeItemForm] Updated item returned", {
        flowLabel,
        itemId: item.id,
        updatedItem,
      });

      await queryClient.invalidateQueries({ queryKey: ["wardrobe"] });
      await queryClient.invalidateQueries({ queryKey: ["wardrobe", "stats"] });
      await onUpdated?.(updatedItem);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <div className="grid gap-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Card className="overflow-hidden border border-border/60">
          <CardContent className="p-0">
            <div className="aspect-square bg-muted">
              <img
                src={item.segmentedImageUrl || item.imageUrl}
                alt={formState.name || item.name}
                className="h-full w-full object-cover"
              />
            </div>
            <div className="space-y-2 p-4">
              <p className="text-sm font-medium text-foreground">
                {formState.name || item.name}
              </p>
              {previewDetails}
            </div>
          </CardContent>
        </Card>

        <MetadataForm
          metadata={formState}
          onChange={setFormState}
          showDescriptionField
        />
      </div>

      <DialogFooter>
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSaving}
          >
            {cancelLabel}
          </Button>
        )}
        <Button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
        >
          {isSaving ? "Saving..." : saveLabel}
        </Button>
      </DialogFooter>
    </>
  );
};
