import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MoreVertical, Edit, Trash2, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { WardrobeItem } from "@/types/wardrobe";

interface WardrobeItemCardProps {
  item: WardrobeItem;
  onEdit?: (item: WardrobeItem) => void;
  onDelete?: (id: string) => void;
  onMarkWorn?: (id: string) => void;
  className?: string;
}

export const WardrobeItemCard = ({
  item,
  onEdit,
  onDelete,
  onMarkWorn,
  className,
}: WardrobeItemCardProps) => {
  const primaryImageSrc = item.segmentedImageUrl || item.imageUrl;
  const fallbackImageSrc = item.imageUrl;
  const [imageError, setImageError] = useState(false);
  const [currentImageSrc, setCurrentImageSrc] = useState(primaryImageSrc);
  const formattedSubcategory = item.subcategory
    ? item.subcategory
        .split("-")
        .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
        .join(" ")
    : undefined;
  const swatchColor = item.swatchColorHex || item.color || "#9CA3AF";
  const displayedColorLabel = item.colorLabel || item.color;

  useEffect(() => {
    console.log("[WardrobeItemCard] Received item subcategory", {
      id: item.id,
      subcategory: item.subcategory,
      category: item.category,
    });
  }, [item.id, item.subcategory, item.category]);

  useEffect(() => {
    console.log("[WardrobeItemCard] Color rendering", {
      id: item.id,
      rawColorValue: item.colorLabel || item.color,
      normalizedColorValue: item.color,
      finalSwatchHex: swatchColor,
    });
  }, [item.id, item.color, item.colorLabel, swatchColor]);

  useEffect(() => {
    setCurrentImageSrc(primaryImageSrc);
    setImageError(false);
  }, [primaryImageSrc]);

  const handleImageError = () => {
    if (currentImageSrc !== fallbackImageSrc) {
      console.warn("[WardrobeItemCard] Segmented image failed, falling back to original", {
        id: item.id,
        segmentedImageUrl: item.segmentedImageUrl,
        originalImageUrl: item.imageUrl,
        subcategory: item.subcategory,
      });
      setCurrentImageSrc(fallbackImageSrc);
      return;
    }

    setImageError(true);
  };

  return (
    <Card className={cn("group overflow-hidden border border-border/60 hover:shadow-lg transition-shadow", className)}>
      <div className="aspect-square overflow-hidden relative bg-muted">
        {!imageError ? (
          <img
            src={currentImageSrc}
            alt={item.name}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={handleImageError}
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="h-full w-full flex items-center justify-center">
            <p className="text-muted-foreground text-sm">Image not available</p>
          </div>
        )}
        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="secondary" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {onEdit && (
                <DropdownMenuItem onClick={() => onEdit(item)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
              )}
              {onMarkWorn && (
                <DropdownMenuItem onClick={() => onMarkWorn(item.id)}>
                  <Calendar className="mr-2 h-4 w-4" />
                  Mark as worn
                </DropdownMenuItem>
              )}
              {onDelete && (
                <DropdownMenuItem
                  onClick={() => onDelete(item.id)}
                  className="text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="absolute bottom-2 left-2">
          <Badge variant="secondary" className="text-xs">
            {item.category}
          </Badge>
        </div>
      </div>
      <CardContent className="p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm text-foreground truncate flex-1">
            {item.name}
          </h3>
        </div>
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground truncate">
            Category: {item.category}
          </p>
          {formattedSubcategory && (
            <p className="text-xs text-muted-foreground truncate">
              Subcategory: {formattedSubcategory}
            </p>
          )}
        </div>
        {item.notes && (
          <p className="text-xs text-muted-foreground line-clamp-2">{item.notes}</p>
        )}
        <div className="flex items-center gap-2 flex-wrap">
          <div
            className="w-3 h-3 rounded-full border border-border"
            style={{ backgroundColor: swatchColor }}
            title={displayedColorLabel || "Unknown color"}
          />
          <span className="text-xs text-muted-foreground">
            {displayedColorLabel || "Unknown"}
          </span>
          <span className="text-xs text-muted-foreground">{item.season}</span>
          {item.wearCount > 0 && (
            <span className="text-xs text-muted-foreground">
              Worn {item.wearCount}x
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

