from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
from http import HTTPStatus

from ..models import Post, Group

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='HasNoName',
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user_not_author = User.objects.create_user(username='LogoutUser')
        self.authorized_not_author = Client()
        self.authorized_not_author.force_login(self.user_not_author)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.user)

    def test_homepage(self):
        """проверяем доступ главной страницы."""
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_group_posts_response(self):
        """проверяем доступ страницы группы guest_client."""
        response = self.guest_client.get('/profile/HasNoName/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_detail_response(self):
        """проверяем доступ страницы информации о посте guest_client."""
        response = self.guest_client.get('/posts/1/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_profile_response(self):
        """проверяем доступ guest_client к странице профиля."""
        response = self.guest_client.get('/profile/HasNoName/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_response(self):
        """проверяем доступ страницы создания поста у guest_client."""
        response = self.guest_client.get('/create/')
        self.assertRedirects(response,
                             reverse('users:login')
                             + '?next=' + reverse('posts:post_create'))

    def test_post_edit_response(self):
        """проверяем доступ страницы редактирования поста у guest_client."""
        response = self.guest_client.get('/posts/1/edit/')
        self.assertRedirects(
            response,
            reverse('users:login')
            + '?next=' + reverse('posts:post_edit', kwargs={'post_id': '1'})
        )

    def test_unexisting_page_response(self):
        """проверяем доступ к несуществующей странице у guest_client."""
        response = self.guest_client.get('unexisting_page')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_follow_page_response(self):
        """Проверяем доступ guest_client к страницам подписок"""
        urls = {
            'follow_index': '/follow/',
            'profile_follow': '/profile/HasNoName/follow/',
            'profile_unfollow': '/profile/HasNoName/unfollow/'
        }
        response_follow_index = self.guest_client.get(
            urls['follow_index']
        )
        self.assertRedirects(response_follow_index, reverse('users:login')
                             + '?next=' + urls['follow_index'])
        response_unfollow = self.guest_client.get(
            urls['profile_unfollow']
        )
        self.assertRedirects(response_unfollow, reverse('users:login')
                             + '?next=' + urls['profile_unfollow'])
        response_follow = self.guest_client.get(
            urls['profile_follow']
        )
        self.assertRedirects(response_follow, reverse('users:login')
                             + '?next=' + urls['profile_follow'])

    def test_urls_authorised(self):
        """проверяем доступы авторизированного клиента(не автора)."""
        urls = {
            'post_edit': '/posts/1/edit/',
            'post_create': '/create/',
            'follow_index': '/follow/',
        }

        response_post_create = self.authorized_not_author.get(
            urls['post_create']
        )
        self.assertEqual(response_post_create.status_code, HTTPStatus.OK)

        response_post_edit = self.authorized_not_author.get(
            urls['post_edit']
        )
        self.assertRedirects(response_post_edit, '/posts/1/')
        response_follow_index = self.authorized_not_author.get(
            urls['follow_index']
        )
        self.assertEqual(response_follow_index.status_code, HTTPStatus.OK)

    def test_urls_author(self):
        """проверяем доступ автора к редактированию поста."""
        response = self.authorized_author.get(
            '/posts/1/edit/'
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """провеяем что адреса используют правильный шаблон"""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/HasNoName/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            '/posts/1/edit/': 'posts/create_post.html',
            'unexisting_page': 'core/404.html',
            '/follow/': 'posts/follow.html'
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_author.get(address)
                self.assertTemplateUsed(response, template)
