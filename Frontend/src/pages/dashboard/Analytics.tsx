import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";
import { Package, RefreshCcw, Shirt, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { wardrobeApi } from "@/lib/api/wardrobe";

const chartConfig = {
  count: { label: "Items", color: "hsl(var(--primary))" },
};

const Analytics = () => {
  const navigate = useNavigate();

  const { data: stats, isLoading } = useQuery({
    queryKey: ["wardrobe", "stats"],
    queryFn: wardrobeApi.getWardrobeStats,
  });

  const { data: suggestions, isLoading: isLoadingSuggestions } = useQuery({
    queryKey: ["wardrobe", "suggestions"],
    queryFn: wardrobeApi.getWardrobeSuggestions,
  });

  const categoryData = stats
    ? Object.entries(stats.itemsByCategory)
        .map(([category, count]) => ({ category, count }))
        .sort((a, b) => b.count - a.count)
    : [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Insights & Analytics</h1>
        <p className="text-muted-foreground mt-2">Track your wardrobe usage and sustainability metrics</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {isLoading ? (
          [...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2"><Skeleton className="h-4 w-24" /></CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-16 mb-1" />
                <Skeleton className="h-3 w-32" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <StatCard icon={<Package className="h-4 w-4" />} label="Total Items" value={stats?.totalItems ?? 0} />
            <StatCard icon={<Shirt className="h-4 w-4" />} label="Total Wears" value={stats?.totalWears ?? 0} />
            <StatCard
              icon={<RefreshCcw className="h-4 w-4" />}
              label="Never Worn"
              value={stats?.neverWorn ?? 0}
              sub="Rediscover these items"
            />
          </>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Category Breakdown</CardTitle>
          <CardDescription>Item count by clothing category</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-[200px] w-full" />
          ) : categoryData.length > 0 ? (
            <ChartContainer config={chartConfig} className="h-[200px]">
              <BarChart data={categoryData} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="category"
                  tick={{ fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                />
                <ChartTooltip content={<ChartTooltipContent />} />
                <Bar dataKey="count" fill="var(--color-count)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ChartContainer>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">No wardrobe items yet</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Most Worn</CardTitle>
            <CardDescription>Your top 5 most frequently worn items</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <ItemListSkeleton />
            ) : stats?.mostWorn.filter((i) => i.wearCount > 0).length ? (
              <div className="space-y-3">
                {stats.mostWorn
                  .filter((i) => i.wearCount > 0)
                  .map((item) => (
                    <div key={item.id} className="flex items-center gap-3">
                      <img
                        src={item.imageUrl}
                        alt={item.name}
                        className="h-10 w-10 rounded-md object-cover bg-muted shrink-0"
                        onError={(e) => {
                          (e.target as HTMLImageElement).style.visibility = "hidden";
                        }}
                      />
                      <span className="flex-1 text-sm font-medium truncate">{item.name}</span>
                      <Badge variant="secondary">{item.wearCount}x</Badge>
                    </div>
                  ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No wear data yet. Mark items as worn from your wardrobe.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recently Worn</CardTitle>
            <CardDescription>Last 5 items you wore</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <ItemListSkeleton />
            ) : stats?.recentlyWorn.length ? (
              <div className="space-y-3">
                {stats.recentlyWorn.map((item) => (
                  <div key={item.id} className="flex items-center gap-3">
                    <img
                      src={item.imageUrl}
                      alt={item.name}
                      className="h-10 w-10 rounded-md object-cover bg-muted shrink-0"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.visibility = "hidden";
                      }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{item.name}</p>
                      {item.lastWorn && (
                        <p className="text-xs text-muted-foreground">
                          {new Date(item.lastWorn).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <Badge variant="outline" className="text-xs shrink-0">
                      {item.category}
                    </Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No recently worn items. Use "Mark as worn" on wardrobe cards.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {!isLoading && (stats?.neverWorn ?? 0) > 0 && (
        <Card className="border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="text-base">Rediscover your wardrobe</CardTitle>
            <CardDescription>
              You have{" "}
              <strong className="text-foreground">{stats!.neverWorn}</strong>{" "}
              item{stats!.neverWorn !== 1 ? "s" : ""} you've never worn. Head to your wardrobe and give them a try!
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Wardrobe Suggestions</CardTitle>
          <CardDescription>Items you haven't worn recently</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoadingSuggestions ? (
            <div className="space-y-2">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-48" />
            </div>
          ) : suggestions ? (
            <>
              <p className="text-sm text-foreground font-medium">{suggestions.message}</p>
              {suggestions.most_underused_category && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Most underused category:</span>
                  <Badge variant="secondary">{suggestions.most_underused_category}</Badge>
                </div>
              )}
              <Button
                size="sm"
                variant="outline"
                className="gap-2"
                onClick={() => navigate("/dashboard/wardrobe")}
              >
                <Sparkles className="h-4 w-4" />
                Rediscover
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
};

const StatCard = ({
  icon,
  label,
  value,
  sub,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  sub?: string;
}) => (
  <Card>
    <CardHeader className="pb-2">
      <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
        {icon}
        {label}
      </CardTitle>
    </CardHeader>
    <CardContent>
      <p className="text-3xl font-semibold text-foreground">{value.toLocaleString()}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </CardContent>
  </Card>
);

const ItemListSkeleton = () => (
  <div className="space-y-3">
    {[...Array(3)].map((_, i) => (
      <div key={i} className="flex items-center gap-3">
        <Skeleton className="h-10 w-10 rounded-md shrink-0" />
        <Skeleton className="h-4 flex-1" />
        <Skeleton className="h-5 w-8" />
      </div>
    ))}
  </div>
);

export default Analytics;
