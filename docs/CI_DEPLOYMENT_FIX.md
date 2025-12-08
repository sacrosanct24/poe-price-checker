# CI Deployment Issue - Resolution

## Problem Statement

On November 30, 2025, the Build Release workflow (run #4) failed when attempting to deploy release v1.4.0. The failure occurred during the "Upload to release" step with the following error:

```
⚠️ Unexpected error fetching GitHub release for tag refs/tags/v1.4.0: 
HttpError: Resource not accessible by integration - 
https://docs.github.com/rest/releases/releases#update-a-release
```

## Root Cause

The `build-release.yml` workflow initially lacked the necessary permissions to upload release assets. The `softprops/action-gh-release@v2` action requires `contents: write` permission to upload files to GitHub releases, which was not explicitly granted in the workflow.

## Solution

### Primary Fix (Already Implemented)
The workflow was updated to include the required permissions:

```yaml
permissions:
  contents: write  # Required for softprops/action-gh-release to upload assets
```

This fix was implemented immediately after the failure and verified with workflow run #5 (manual dispatch), which completed successfully.

### Additional Improvement (This PR)
Updated the token configuration to follow the recommended approach for `softprops/action-gh-release@v2`:

**Before:**
```yaml
- name: Upload to release
  uses: softprops/action-gh-release@v2
  with:
    files: dist/PoE-Price-Checker.exe
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**After:**
```yaml
- name: Upload to release
  uses: softprops/action-gh-release@v2
  with:
    files: dist/PoE-Price-Checker.exe
    token: ${{ secrets.GITHUB_TOKEN }}
```

The token should be passed as a `with:` parameter rather than an environment variable, which is the standard practice for GitHub Actions v2+.

## Verification

### Successful Releases Post-Fix
After the initial fix was applied, the following releases completed successfully:
- **v1.5.0** (Dec 5, 2025) - AI Analysis & UX Improvements
- **v1.6.0** (Dec 7, 2025) - 3-Screen Architecture

### Testing
The workflow syntax has been validated using YAML parsing and the configuration follows GitHub Actions best practices.

## Key Takeaways

1. **Always specify workflow permissions**: GitHub Actions has moved to a more secure model where workflows need explicit permission grants for sensitive operations.

2. **Use recommended action parameters**: While `env:` variables may work, using the documented `with:` parameters ensures better compatibility and follows best practices.

3. **Monitor workflow runs**: The issue was caught and fixed quickly because the workflow logs provided clear error messages about the permission issue.

## References

- [GitHub Actions: Permissions](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token)
- [softprops/action-gh-release](https://github.com/softprops/action-gh-release)
- [GitHub REST API: Releases](https://docs.github.com/rest/releases/releases#update-a-release)
