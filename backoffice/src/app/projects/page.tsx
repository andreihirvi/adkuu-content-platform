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
import { PageHeader, EmptyState } from '@/components/shared';
import {
  useProjects,
  useCreateProject,
  useUpdateProject,
  useDeleteProject,
} from '@/hooks/use-queries';
import type { Project } from '@/types';

// Import AlertDialog components separately since they weren't included in initial shadcn setup
// Using Dialog as fallback for now

export default function ProjectsPage() {
  const { data: projects, isLoading } = useProjects();
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const deleteProject = useDeleteProject();

  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [deletingProject, setDeletingProject] = useState<Project | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    product_url: '',
    keywords: '',
    tone_guidelines: '',
    target_subreddits: '',
    is_active: true,
    daily_comment_limit: 10,
  });

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      product_url: '',
      keywords: '',
      tone_guidelines: '',
      target_subreddits: '',
      is_active: true,
      daily_comment_limit: 10,
    });
  };

  const handleCreate = () => {
    createProject.mutate(
      {
        name: formData.name,
        description: formData.description || null,
        product_url: formData.product_url || null,
        keywords: formData.keywords.split(',').map((k) => k.trim()).filter(Boolean),
        tone_guidelines: formData.tone_guidelines || null,
        target_subreddits: formData.target_subreddits.split(',').map((s) => s.trim()).filter(Boolean),
        is_active: formData.is_active,
        daily_comment_limit: formData.daily_comment_limit,
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
          product_url: formData.product_url || null,
          keywords: formData.keywords.split(',').map((k) => k.trim()).filter(Boolean),
          tone_guidelines: formData.tone_guidelines || null,
          target_subreddits: formData.target_subreddits.split(',').map((s) => s.trim()).filter(Boolean),
          is_active: formData.is_active,
          daily_comment_limit: formData.daily_comment_limit,
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
      product_url: project.product_url || '',
      keywords: project.keywords?.join(', ') || '',
      tone_guidelines: project.tone_guidelines || '',
      target_subreddits: project.target_subreddits?.join(', ') || '',
      is_active: project.is_active,
      daily_comment_limit: project.daily_comment_limit,
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
          {projects.map((project) => (
            <Card key={project.id}>
              <CardHeader className="flex flex-row items-start justify-between space-y-0">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {project.name}
                    <Badge variant={project.is_active ? 'default' : 'secondary'}>
                      {project.is_active ? 'Active' : 'Inactive'}
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
                    <span>Daily limit: {project.daily_comment_limit}</span>
                    {project.product_url && (
                      <a
                        href={project.product_url}
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
          ))}
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
          <div className="grid gap-4 py-4">
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
                <Label htmlFor="product_url">Product URL</Label>
                <Input
                  id="product_url"
                  value={formData.product_url}
                  onChange={(e) => setFormData({ ...formData, product_url: e.target.value })}
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
              <Label htmlFor="target_subreddits">Target Subreddits (comma-separated)</Label>
              <Input
                id="target_subreddits"
                value={formData.target_subreddits}
                onChange={(e) => setFormData({ ...formData, target_subreddits: e.target.value })}
                placeholder="entrepreneur, startups, productivity"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tone_guidelines">Tone Guidelines</Label>
              <Textarea
                id="tone_guidelines"
                value={formData.tone_guidelines}
                onChange={(e) => setFormData({ ...formData, tone_guidelines: e.target.value })}
                placeholder="Be helpful and authentic. Avoid direct promotion..."
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="daily_limit">Daily Comment Limit</Label>
                <Input
                  id="daily_limit"
                  type="number"
                  min={1}
                  max={100}
                  value={formData.daily_comment_limit}
                  onChange={(e) =>
                    setFormData({ ...formData, daily_comment_limit: parseInt(e.target.value) || 10 })
                  }
                />
              </div>
              <div className="flex items-center space-x-2 pt-6">
                <Switch
                  id="is_active"
                  checked={formData.is_active}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
                />
                <Label htmlFor="is_active">Active</Label>
              </div>
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
