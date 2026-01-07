'use client';

import { useState } from 'react';
import { Plus, MoreVertical, Pencil, Trash2, Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { PageHeader, EmptyState } from '@/components/shared';
import {
  useProjects,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
  useRedditAccounts,
} from '@/hooks/use-queries';
import type { Project } from '@/types';
import { SUPPORTED_LANGUAGES } from '@/types';

// Import AlertDialog components separately since they weren't included in initial shadcn setup
// Using Dialog as fallback for now

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const { data: accounts } = useRedditAccounts();
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [deletingProject, setDeletingProject] = useState<Project | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    website_url: '',
    keywords: '',
    negative_keywords: '',
    brand_voice: '',
    product_context: '',
    target_subreddits: '',
    automation_level: 1 as 1 | 2 | 3 | 4,
    language: '',  // Empty string means no language filter (all languages)
    posting_mode: 'rotate' as 'rotate' | 'specific',
    preferred_account_id: null as number | null,
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      website_url: '',
      keywords: '',
      negative_keywords: '',
      brand_voice: '',
      product_context: '',
      target_subreddits: '',
      automation_level: 1 as 1 | 2 | 3 | 4,
      language: '',
      posting_mode: 'rotate' as 'rotate' | 'specific',
      preferred_account_id: null,
    });
  };

  const handleCreate = () => {
    createProject.mutate(
      {
        name: formData.name,
        description: formData.description || null,
        website_url: formData.website_url || null,
        keywords: formData.keywords.split(',').map((k) => k.trim()).filter(Boolean),
        negative_keywords: formData.negative_keywords.split(',').map((k) => k.trim()).filter(Boolean),
        brand_voice: formData.brand_voice || null,
        product_context: formData.product_context || null,
        target_subreddits: formData.target_subreddits.split(',').map((s) => s.trim()).filter(Boolean),
        automation_level: formData.automation_level,
        language: formData.language || null,
        posting_mode: formData.posting_mode,
        preferred_account_id: formData.posting_mode === 'specific' ? formData.preferred_account_id : null,
      },
      {
        onSuccess: () => {
          setShowCreateDialog(false);
          resetForm();
        },
      }
    );
  };

  const handleUpdate = () => {
    if (!editingProject) return;
    updateProject.mutate(
      {
        id: editingProject.id,
        data: {
          name: formData.name,
          description: formData.description || null,
          website_url: formData.website_url || null,
          keywords: formData.keywords.split(',').map((k) => k.trim()).filter(Boolean),
          negative_keywords: formData.negative_keywords.split(',').map((k) => k.trim()).filter(Boolean),
          brand_voice: formData.brand_voice || null,
          product_context: formData.product_context || null,
          target_subreddits: formData.target_subreddits.split(',').map((s) => s.trim()).filter(Boolean),
          automation_level: formData.automation_level,
          language: formData.language || null,
          posting_mode: formData.posting_mode,
          preferred_account_id: formData.posting_mode === 'specific' ? formData.preferred_account_id : null,
        },
      },
      {
        onSuccess: () => {
          setEditingProject(null);
          resetForm();
        },
      }
    );
  };

  const handleDelete = () => {
    if (!deletingProject) return;
    deleteProject.mutate(deletingProject.id, {
      onSuccess: () => {
        setDeletingProject(null);
      },
    });
  };

  const startEditing = (project: Project) => {
    setFormData({
      name: project.name,
      description: project.description || '',
      website_url: project.website_url || '',
      keywords: project.keywords?.join(', ') || '',
      negative_keywords: project.negative_keywords?.join(', ') || '',
      brand_voice: project.brand_voice || '',
      product_context: project.product_context || '',
      target_subreddits: project.target_subreddits?.join(', ') || '',
      automation_level: project.automation_level || 1,
      language: project.language || '',
      posting_mode: project.posting_mode || 'rotate',
      preferred_account_id: project.preferred_account_id,
    });
    setEditingProject(project);
  };

  return (
    <div>
      <PageHeader
        title="Projects"
        description="Manage your products and services for Reddit promotion"
        actions={
          <Button onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-full" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : !projects?.length ? (
        <EmptyState
          title="No projects yet"
          description="Create your first project to start promoting on Reddit"
          action={{
            label: 'Create Project',
            onClick: () => setShowCreateDialog(true),
          }}
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => {
            const languageName = project.language
              ? SUPPORTED_LANGUAGES.find(l => l.code === project.language)?.name || project.language
              : null;
            return (
              <Card key={project.id}>
                <CardHeader className="flex flex-row items-start justify-between space-y-0">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {project.name}
                      <Badge variant={project.status === 'active' ? 'default' : 'secondary'}>
                        {project.status === 'active' ? 'Active' : project.status === 'paused' ? 'Paused' : 'Archived'}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {project.description || 'No description'}
                    </CardDescription>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => startEditing(project)}>
                        <Pencil className="mr-2 h-4 w-4" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem>
                        <Settings2 className="mr-2 h-4 w-4" />
                        Subreddit Settings
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={() => setDeletingProject(project)}
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {project.target_subreddits?.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-1">Target Subreddits</p>
                        <div className="flex flex-wrap gap-1">
                          {project.target_subreddits.slice(0, 5).map((sub) => (
                            <Badge key={sub} variant="outline">
                              r/{sub}
                            </Badge>
                          ))}
                          {project.target_subreddits.length > 5 && (
                            <Badge variant="outline">
                              +{project.target_subreddits.length - 5} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    {project.keywords?.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-1">Keywords</p>
                        <div className="flex flex-wrap gap-1">
                          {project.keywords.slice(0, 3).map((kw) => (
                            <Badge key={kw} variant="secondary">
                              {kw}
                            </Badge>
                          ))}
                          {project.keywords.length > 3 && (
                            <Badge variant="secondary">
                              +{project.keywords.length - 3} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="flex items-center justify-between text-sm text-muted-foreground pt-2 border-t">
                      {languageName ? (
                        <span>Language: {languageName}</span>
                      ) : (
                        <span>All languages</span>
                      )}
                      {project.website_url && (
                        <a
                          href={project.website_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:underline"
                        >
                          Visit site
                        </a>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog
        open={showCreateDialog || !!editingProject}
        onOpenChange={(open) => {
          if (!open) {
            setShowCreateDialog(false);
            setEditingProject(null);
            resetForm();
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingProject ? 'Edit Project' : 'Create New Project'}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4 max-h-[70vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Project Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Product"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="website_url">Website URL</Label>
                <Input
                  id="website_url"
                  value={formData.website_url}
                  onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
                  placeholder="https://example.com"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Brief description of your product..."
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="keywords">Keywords (comma-separated)</Label>
                <Input
                  id="keywords"
                  value={formData.keywords}
                  onChange={(e) => setFormData({ ...formData, keywords: e.target.value })}
                  placeholder="productivity, automation, saas"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="negative_keywords">Negative Keywords (comma-separated)</Label>
                <Input
                  id="negative_keywords"
                  value={formData.negative_keywords}
                  onChange={(e) => setFormData({ ...formData, negative_keywords: e.target.value })}
                  placeholder="spam, scam, competitor"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="target_subreddits">Target Subreddits (comma-separated)</Label>
              <Input
                id="target_subreddits"
                value={formData.target_subreddits}
                onChange={(e) => setFormData({ ...formData, target_subreddits: e.target.value })}
                placeholder="entrepreneur, startups, productivity"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="language">Content Language</Label>
                <Select
                  value={formData.language}
                  onValueChange={(value) => setFormData({ ...formData, language: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="All languages (no filter)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All languages (no filter)</SelectItem>
                    {SUPPORTED_LANGUAGES.map((lang) => (
                      <SelectItem key={lang.code} value={lang.code}>
                        {lang.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Only mine posts in this language and generate content in this language
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="automation_level">Automation Level</Label>
                <Select
                  value={formData.automation_level.toString()}
                  onValueChange={(value) => setFormData({ ...formData, automation_level: parseInt(value) as 1 | 2 | 3 | 4 })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Manual - All content needs review</SelectItem>
                    <SelectItem value="2">Assisted - High confidence queued</SelectItem>
                    <SelectItem value="3">Semi-Auto - Safe content auto-approved</SelectItem>
                    <SelectItem value="4">Full Auto - ML-driven publishing</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="brand_voice">Brand Voice Guidelines</Label>
              <Textarea
                id="brand_voice"
                value={formData.brand_voice}
                onChange={(e) => setFormData({ ...formData, brand_voice: e.target.value })}
                placeholder="Be helpful and authentic. Avoid direct promotion..."
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="product_context">Product Context</Label>
              <Textarea
                id="product_context"
                value={formData.product_context}
                onChange={(e) => setFormData({ ...formData, product_context: e.target.value })}
                placeholder="What your product does, key features, unique selling points..."
                rows={2}
              />
            </div>

            {/* Account Selection */}
            <div className="border-t pt-4 mt-4">
              <h4 className="font-medium mb-3">Posting Account Settings</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="posting_mode">Account Selection Mode</Label>
                  <Select
                    value={formData.posting_mode}
                    onValueChange={(value: 'rotate' | 'specific') => {
                      setFormData({
                        ...formData,
                        posting_mode: value,
                        // Reset preferred account if switching to rotate
                        preferred_account_id: value === 'rotate' ? null : formData.preferred_account_id
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="rotate">Rotate All Accounts</SelectItem>
                      <SelectItem value="specific">Use Specific Account</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {formData.posting_mode === 'rotate'
                      ? 'Posts will be distributed across all connected accounts'
                      : 'All posts will be made from the selected account'}
                  </p>
                </div>
                {formData.posting_mode === 'specific' && (
                  <div className="space-y-2">
                    <Label htmlFor="preferred_account">Select Account</Label>
                    <Select
                      value={formData.preferred_account_id?.toString() || ''}
                      onValueChange={(value) => setFormData({
                        ...formData,
                        preferred_account_id: value ? parseInt(value) : null
                      })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Choose an account" />
                      </SelectTrigger>
                      <SelectContent>
                        {accounts?.filter(a => a.status === 'active').map((account) => (
                          <SelectItem key={account.id} value={account.id.toString()}>
                            u/{account.username} ({account.karma_total.toLocaleString()} karma)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>
              {!accounts?.length && (
                <p className="text-sm text-muted-foreground mt-2">
                  No Reddit accounts connected. Connect accounts in the Accounts page.
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowCreateDialog(false);
                setEditingProject(null);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={editingProject ? handleUpdate : handleCreate}
              disabled={!formData.name || createProject.isPending || updateProject.isPending}
            >
              {editingProject ? 'Save Changes' : 'Create Project'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deletingProject} onOpenChange={() => setDeletingProject(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Project</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground">
            Are you sure you want to delete "{deletingProject?.name}"? This action cannot be undone.
            All associated opportunities and content will also be deleted.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingProject(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteProject.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
