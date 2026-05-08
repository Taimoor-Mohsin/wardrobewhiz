import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/hooks/use-auth";

const Settings = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-2">
          Manage account and app preferences. Style profile editing now lives on the Profile page.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>Basic account details from your signed-in session.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input placeholder="Full name" value={user?.name || ""} readOnly />
            <Input placeholder="Email" value={user?.email || ""} readOnly />
            <Button className="w-full sm:w-auto" disabled>
              Account editing coming soon
            </Button>
          </CardContent>
        </Card>

        <Card className="shadow-card">
          <CardHeader>
            <CardTitle>App preferences</CardTitle>
            <CardDescription>Interface options will be configurable in a later phase.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { id: "compact", label: "Compact dashboard", description: "Use denser layouts for wardrobe management." },
              { id: "dark", label: "Dark mode", description: "Follow your preferred low-light interface." },
            ].map((pref) => (
              <div key={pref.id} className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-foreground">{pref.label}</p>
                  <p className="text-sm text-muted-foreground">{pref.description}</p>
                </div>
                <Switch id={pref.id} disabled />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-card">
        <CardHeader>
          <CardTitle>Notification preferences</CardTitle>
          <CardDescription>Toggle the nudges you care about.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { id: "looks", label: "New outfit drops", description: "Daily email when fresh combos are ready." },
            { id: "sustainability", label: "Sustainability reminders", description: "Weekly note on rewear stats." },
            { id: "alerts", label: "Weather alerts", description: "SMS when weather conflicts with planned outfits." },
          ].map((pref) => (
            <div key={pref.id} className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-foreground">{pref.label}</p>
                <p className="text-sm text-muted-foreground">{pref.description}</p>
              </div>
              <Switch id={pref.id} defaultChecked />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};

export default Settings;
