from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Comment, Group, Post

User = get_user_model()

NUMBER_OF_LETTERS = 15


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост в тестовой группе и вообще в тесте',
        )

    def test_str_post(self):
        """Проверяем, что у модели Post работает __str__."""
        post = PostModelTest.post
        expected_post_str = post.text[:NUMBER_OF_LETTERS]
        self.assertEqual(expected_post_str, str(post))


class GroupModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )

    def test_str_group(self):
        """Проверяем, что у модели Group работает __str__."""
        group = GroupModelTest.group
        expected_group_str = group.title
        self.assertEqual(expected_group_str, str(group))


class CommentModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.user_2 = User.objects.create_user(username='Leha')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост в тестовой группе и вообще в тесте',
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user_2,
            text='Тестовый коммент'
        )

    def test_str_comment(self):
        comment = CommentModelTest.comment
        expected_comment_str = comment.text[:NUMBER_OF_LETTERS]
        self.assertEqual(expected_comment_str, str(comment))
