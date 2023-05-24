import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from http import HTTPStatus
from django.core.cache import cache

from ..models import Comment, Group, Post

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='author',
        )
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.non_author = Client()
        cls.non_author.force_login
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='group-slug'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_cache(self):
        """Проверяем кэширование главной страницы"""
        response_1 = self.authorized_client.get(reverse('posts:index'))
        post_1 = Post.objects.get(id=1)
        post_1.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_1.content, response_3.content)

    def test_post_create(self):
        """Проверяем, создается ли пост в БД."""
        post_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Текст из формы',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(Post.objects.filter(
            text=form_data['text'],
            group=form_data['group'],
            author=self.user,
            image='posts/small.gif'
        ).exists())

    def test_edit_post(self):
        """Проверяем, редактируется ли пост в БД."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Измененный текст из формы',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(
            id=self.post.id,
            text=form_data['text'],
            group=form_data['group'],
            author=self.post.author,
            pub_date=self.post.pub_date,
        ).exists())

    def test_add_comment(self):
        """Проверяем, создается ли комментарий к посту"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'тестовый текст тестового комента',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comments_count + 1)

    def test_guest_client_redirect_when_create_post(self):
        """Проверка редиректа неавторизированного
        пользователя при создании поста"""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Текст из формы',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        self.assertRedirects(
            response,
            reverse('users:login') + '?next=' + reverse('posts:post_create')
        )
        self.assertEqual(Post.objects.count(), post_count)

    def test_guest_client_redirect_when_edit_post(self):
        """Проверка редиректа неавторизированного
        пользователя при редактировании поста"""
        form_data = {
            'text': 'Измененный текст из формы',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        edit_object = Post.objects.get(id=self.post.id)
        self.assertEqual(edit_object.text, self.post.text)
        self.assertEqual(edit_object.author, self.post.author)
        self.assertEqual(edit_object.group, self.post.group)
        self.assertEqual(edit_object.pub_date, self.post.pub_date)
        self.assertRedirects(
            response,
            reverse('users:login')
            + '?next=' + reverse('posts:post_edit',
                                 kwargs={'post_id': self.post.id}))

    def test_authorized_non_author_redirect(self):
        """Проверка редиректа не автора при редактировании поста."""
        form_data = {
            'text': 'Измененный текст из формы',
            'group': self.group.id,
        }
        response = self.non_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        edit_object = Post.objects.get(id=self.post.id)
        self.assertEqual(edit_object.text, self.post.text)
        self.assertEqual(edit_object.author, self.post.author)
        self.assertEqual(edit_object.group, self.post.group)
        self.assertEqual(edit_object.pub_date, self.post.pub_date)
        self.assertRedirects(
            response,
            reverse('users:login')
            + '?next=' + reverse('posts:post_edit',
                                 kwargs={'post_id': self.post.id}))

    def test_create_post_without_group(self):
        """Проверяем, создастся ли пост без указания группы"""
        post_count = Post.objects.count()
        form_data = {
            'text': 'Текст из формы',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(Post.objects.filter(
            text=form_data['text'],
            group=None,
            author=self.user,
        ).exists())

    def test_guest_client_redirect_when_add_comment(self):
        """Проверка редиректа неавторизированного
        пользователя при добавлении коммента"""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Текст нового комментария',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(Comment.objects.count(), comments_count)
        self.assertRedirects(
            response,
            reverse('users:login')
            + '?next=' + reverse('posts:add_comment',
                                 kwargs={'post_id': self.post.id}))
