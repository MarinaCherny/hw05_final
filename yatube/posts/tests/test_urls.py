from http import HTTPStatus

from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, User


class PostUrlsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='test_user'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post_author = Client()
        cls.post_author.force_login(cls.post.author)

    def test_url_available_to_anyone(self):
        """Проверка общедоступных страниц"""
        pages = {
            reverse('posts:home'): 'posts/index.html',
            reverse('posts:group_posts',
                    kwargs={'slug': f'{self.group.slug}'}):
                        'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}):
                        'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': f'{self.post.id}'}):
                        'posts/post_detail.html',
        }
        for page in pages:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_avaliable_to_authorized_client(self):
        """Проверка страниц доступных авторизованным пользователям"""
        pages = {
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html'
        }
        for page in pages:
            with self.subTest(page=page):
                response = self.authorized_client.get(page)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_available_to_author_post(self):
        """Проверка доступности поста автору"""
        response = self.post_author.get(reverse(
            'posts:post_edit', kwargs={'post_id': f'{self.post.id}'}
        ))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """Проверка шаблонов по адресам"""
        templates_url_names = {
            reverse('posts:home'): 'posts/index.html',
            reverse('posts:group_posts',
                    kwargs={'slug': f'{self.group.slug}'}):
                        'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': f'{self.user.username}'}):
                        'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': f'{self.post.id}'}):
                        'posts/post_detail.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': f'{self.post.id}'}):
                        'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }

        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.post_author.get(url)
                self.assertTemplateUsed(response, template)

    def test_url_unexisting_page(self):
        """Проверка несуществующая страница выдает ошибку 404
        с кастомным шаблоном"""
        response = self.client.get('/unexisting_page/')
        custom_template_404 = 'core/404.html'
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, custom_template_404)

    def test_redirect_non_author(self):
        """Проверка редиректа неавтора поста """
        not_author = User.objects.create_user(username='test_not_author')
        not_author_client = Client()
        not_author_client.force_login(not_author)
        response = not_author_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': f'{self.post.id}'}))
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': f'{self.post.id}'}))
