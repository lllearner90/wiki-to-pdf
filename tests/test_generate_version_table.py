import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Ensure the src directory is in the path to import generate_version_table
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from generate_version_table import build_version_table, is_git_repo


class TestGitVersionHistory(unittest.TestCase):
    def setUp(self):
        """Set up a temporary git repository for testing."""
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize a new git repository
        subprocess.run(['git', 'init', '--initial-branch=main'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], check=True, capture_output=True)

    def tearDown(self):
        """Clean up the temporary directory."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def commit(self, message: str, date_ts: int = None):
        """Helper to create a git commit with a dummy file change."""
        with open('dummy.txt', 'a') as f:
            f.write(f'{message}\n')
        
        env = os.environ.copy()
        if date_ts:
            env['GIT_AUTHOR_DATE'] = f"{date_ts} +0000"
            env['GIT_COMMITTER_DATE'] = f"{date_ts} +0000"
            
        subprocess.run(['git', 'add', 'dummy.txt'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', message], check=True, capture_output=True, env=env)

    def tag(self, name: str, message: str = None, date_ts: int = None):
        """Helper to create a git tag."""
        env = os.environ.copy()
        if date_ts:
            env['GIT_COMMITTER_DATE'] = f"{date_ts} +0000"

        if message:
            subprocess.run(['git', 'tag', '-a', name, '-m', message], check=True, capture_output=True, env=env)
        else:
            subprocess.run(['git', 'tag', name], check=True, capture_output=True, env=env)

    def test_is_git_repo(self):
        """Verify that the temp directory is correctly identified as a git repo."""
        self.assertTrue(is_git_repo())

    def test_no_commits(self):
        """Test behavior when the repository has no commits yet."""
        entries = build_version_table()
        self.assertEqual(entries, [])

    def test_no_tags(self):
        """Test behavior with commits but no tags (everything is 'Unreleased')."""
        self.commit('Initial commit')
        self.commit('Feature 1')

        entries = build_version_table()
        self.assertEqual(len(entries), 1)
        
        entry = entries[0]
        self.assertEqual(entry['version'], 'Unreleased')
        self.assertEqual(entry['author'], 'Test User')
        
        # Commits are returned newest first
        self.assertEqual(len(entry['changes']), 2)
        self.assertEqual(entry['changes'][0], 'Feature 1')
        self.assertEqual(entry['changes'][1], 'Initial commit')

    def test_with_tags_and_unreleased(self):
        """Test grouping of commits between tags and unreleased commits."""
        self.commit('Initial commit', date_ts=1700000000)
        self.tag('v1.0.0', 'First release', date_ts=1700000010)
        self.commit('Feature 2', date_ts=1700000020)
        self.tag('v2.0.0', 'Second release', date_ts=1700000030)
        self.commit('WIP Feature', date_ts=1700000040)
        self.commit('Another WIP', date_ts=1700000050)

        entries = build_version_table()
        
        # Expect 3 groups: Unreleased, v2.0.0, v1.0.0
        self.assertEqual(len(entries), 3)
        
        # Unreleased block
        self.assertEqual(entries[0]['version'], 'Unreleased')
        self.assertEqual(entries[0]['changes'][0], 'Another WIP')
        self.assertEqual(entries[0]['changes'][1], 'WIP Feature')
        self.assertNotIn('Second release', entries[0]['changes'])

        # v2.0.0 block
        self.assertEqual(entries[1]['version'], 'v2.0.0')
        self.assertEqual(entries[1]['changes'][0], 'Second release') # Tag message
        self.assertEqual(entries[1]['changes'][1], 'Feature 2')
        self.assertNotIn('First release', entries[1]['changes'])

        # v1.0.0 block
        self.assertEqual(entries[2]['version'], 'v1.0.0')
        self.assertEqual(entries[2]['changes'][0], 'First release') # Tag message
        self.assertEqual(entries[2]['changes'][1], 'Initial commit')

    def test_lightweight_tags(self):
        """Test handling of lightweight tags (no tag message)."""
        self.commit('Initial commit')
        self.tag('v1.0.0') # Lightweight tag

        entries = build_version_table()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['version'], 'v1.0.0')
        self.assertEqual(entries[0]['changes'][0], 'Initial commit')

    def test_exclude_pattern(self):
        """Test filtering commits using a regex pattern."""
        self.commit('Initial commit')
        self.commit('Merge branch X')
        self.commit('chore: update deps')
        self.commit('Feature 1')

        entries = build_version_table(exclude_pattern=r"^(Merge|chore:)")
        self.assertEqual(len(entries), 1)
        
        changes = entries[0]['changes']
        self.assertEqual(len(changes), 2)
        self.assertIn('Feature 1', changes)
        self.assertIn('Initial commit', changes)
        self.assertNotIn('Merge branch X', changes)
        self.assertNotIn('chore: update deps', changes)

    def test_max_commits_truncation(self):
        """Test truncation of changes list when it exceeds max_commits."""
        for i in range(5):
            self.commit(f'Commit {i}')

        entries = build_version_table(max_commits=2)
        changes = entries[0]['changes']
        
        # Should contain 2 actual commits + 1 truncation message
        self.assertEqual(len(changes), 3)
        self.assertEqual(changes[0], 'Commit 4')
        self.assertEqual(changes[1], 'Commit 3')
        self.assertEqual(changes[2], '… and 3 more')

    def test_no_unreleased_flag(self):
        """Test the --no-unreleased flag behavior."""
        self.commit('Initial commit')
        self.tag('v1.0.0', 'Release')
        self.commit('Unreleased commit')

        entries = build_version_table(include_unreleased=False)
        
        # Should only contain the v1.0.0 block
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['version'], 'v1.0.0')
        self.assertNotIn('Unreleased commit', entries[0]['changes'])


if __name__ == '__main__':
    unittest.main()
