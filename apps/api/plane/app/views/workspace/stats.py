# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import Workspace, Project, Issue
from ..base import BaseAPIView
from plane.app.permissions import allow_permission, ROLE


class WorkspaceStatsEndpoint(BaseAPIView):
    """
    Endpoint to get statistics for a workspace
    """

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        """
        Get workspace statistics including project count, issue count, and member count
        """
        try:
            workspace = Workspace.objects.get(slug=slug)

            # Get counts
            project_count = Project.objects.filter(workspace=workspace).count()
            issue_count = Issue.objects.filter(workspace=workspace).count()
            member_count = workspace.workspace_member.count()

            stats = {
                "workspace_id": str(workspace.id),
                "workspace_slug": workspace.slug,
                "workspace_name": workspace.name,
                "total_projects": project_count,
                "total_issues": issue_count,
                "total_members": member_count,
                "created_at": workspace.created_at.isoformat(),
            }

            return Response(stats, status=status.HTTP_200_OK)
        except Workspace.DoesNotExist:
            return Response(
                {"error": "Workspace not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
