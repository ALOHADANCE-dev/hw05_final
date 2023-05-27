import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from posts.models import Post, Group, Follow

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
NUMBER_OF_CREATED_POST = 11
POSTS_ON_FIRST_PAGE = 10
POSTS_ON_SECOND_PAGE = 2


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='HasNoName',
        )
        cls.follower = User.objects.create_user(
            username='follower',
        )
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.followerized_client = Client()
        cls.followerized_client.force_login(cls.follower)
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
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.fake_group = Group.objects.create(
            title='Ложный заголовок',
            description='Ложное описание',
            slug='fake-slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        )
        Post.objects.bulk_create([Post(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,
        ) for q in range(NUMBER_OF_CREATED_POST)])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug':
                            f'{self.group.slug}'}): 'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username':
                            f'{self.user.username}'}): 'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
                        'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}):
                        'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_all(self, post):
        self.assertEqual(post.text, PostPagesTests.post.text)
        self.assertEqual(post.group.id, PostPagesTests.group.id)
        self.assertEqual(post.author, PostPagesTests.user)
        self.assertEqual(self.post.pub_date,
                         PostPagesTests.post.pub_date)
        self.assertEqual(self.post.image, PostPagesTests.post.image)

    def test_index_page_show_correct_context(self):
        """проверяем, что в шаблон главное передается правильный контекст"""
        response = self.guest_client.get(reverse('posts:index'))
        self.check_all(response.context['page_obj'][0])

    def test_group_list_page_show_correct_context(self):
        """проверяем, что в шаблон группы передается правильный контекст"""
        response = self.guest_client.get(
            reverse(('posts:group_list'), kwargs={'slug': self.group.slug})
        )
        self.check_all(response.context['page_obj'][0])
        self.assertEqual(response.context['group'], self.group)

    def test_profile_page_show_correct_context(self):
        """проверяем, что в шаблон профиля передается правильный контекст"""
        response = self.guest_client.get(
            reverse(('posts:profile'), kwargs={'username': self.user.username})
        )
        self.check_all(response.context['page_obj'][0])
        self.assertEqual(response.context['author'], self.user)

    def test_post_detail_page_show_correct_context(self):
        """
        проверяем, что в шаблон информации о посте передается правильный
        контекст
        """
        response = self.authorized_client.get(
            reverse(('posts:post_detail'), kwargs={'post_id': self.post.id})
        )
        self.check_all(response.context.get('post'))
        form = response.context.get('form')
        self.assertIsNotNone(form.fields)
        comments = response.context.get('comments')
        self.assertEqual(len(comments), self.post.comments.count())

    def test_create_post_page_show_correct_context(self):
        """
        проверяем, что в шаблон создания поста передается правильный
        контекст
        """
        response = self.authorized_client.get(
            reverse('posts:post_create'),
            follow=True,
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertFalse(response.context.get('is_edit'))

    def test_edit_post_page_show_correct_context(self):
        """
        проверяем, что в шаблон редактирования поста передается правильный
        контекст
        """
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}),
            follow=True,
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context.get('is_edit'))

    def test_first_page_contains_ten_posts(self):
        """проверяем, что на первой странице 10 постов"""
        # это скорее всего грязно так писать, но пока не определился куда
        # если писать в сетап класс, то ломаются другие тесты
        self.followerized_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': 'HasNoName'}))
        page_names_args = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': 'HasNoName'}),
            reverse('posts:follow_index')
        )
        for url_test in page_names_args:
            response = self.followerized_client.get(url_test)
            self.assertEqual(len(response.context['page_obj']),
                             POSTS_ON_FIRST_PAGE)

    def test_second_page(self):
        """проверяем, что на второй странице 2 поста"""
        self.followerized_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': 'HasNoName'}))
        page_names_args = (
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list',
                    kwargs={'slug': 'test-slug'}) + '?page=2',
            reverse('posts:profile',
                    kwargs={'username': 'HasNoName'}) + '?page=2',
            reverse('posts:follow_index') + '?page=2',
        )
        for url in page_names_args:
            response = self.followerized_client.get(url)
            self.assertEqual(len(response.context['page_obj']),
                             POSTS_ON_SECOND_PAGE)

    def test_post_on_the_correct_page(self):
        """проверяем, что посты после создания правильно размещаются"""
        pages = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile',
                    kwargs={'username': self.user.username}),
        )
        for page in pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                first_object = response.context['page_obj'][0]
                post_text = first_object.text
                post_group = first_object.group
                self.assertEqual(post_text, PostPagesTests.post.text)
                self.assertEqual(post_group, PostPagesTests.group)
                self.assertNotEqual(post_group, self.fake_group)

    def test_follow(self):
        """Проверям подписку на пользователя"""
        followers_count = Follow.objects.count()
        self.followerized_client.post(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user}
            )
        )
        self.assertEqual(Follow.objects.count(), followers_count + 1)
        follow = Follow.objects.latest('id')
        self.assertEqual(follow.user, self.follower)
        self.assertEqual(follow.author, self.user)

    def test_unfollow(self):
        """Проверям отпписку от пользователя"""
        Follow.objects.create(
            user=self.user,
            author=self.follower,
        )
        followers_count = Follow.objects.count()
        self.authorized_client.post(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.follower.username}
            )
        )
        self.assertEqual(Follow.objects.count(), followers_count - 1)

    def test_posts_follows(self):
        """Проверям отображение постов на странице избранных авторов"""
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
        )
        Follow.objects.create(
            author=self.user,
            user=self.follower,
        )
        response = self.followerized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_posts_followers(self):
        """Проверям, что без подписки посты не попадают в блок подписок"""
        response = self.followerized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(self.post, response.context['page_obj'].object_list)

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
