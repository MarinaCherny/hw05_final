import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='test_user'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост ',
            image=cls.uploaded,
            group=cls.group
        )
        cls.authorized_client = Client()
        # Авторизуем пользователя
        cls.authorized_client.force_login(cls.user)
        # Пользователь является автором
        cls.authorized_client.force_login(cls.post.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def check_post_context(self, source_post, compared_post):
        self.assertEqual(source_post.author, compared_post.author)
        self.assertEqual(source_post.group, compared_post.group)
        self.assertEqual(source_post.image, compared_post.image)
        self.assertEqual(source_post.pub_date, compared_post.pub_date)
        self.assertEqual(source_post.text, compared_post.text)

    def test_home_page_show_correct_context(self):
        """Проверка контекста: home сформирован с правильным контекстом,
        включена проверка вывода изображения."""
        response = self.authorized_client.get(reverse('posts:home'))
        self.check_post_context(self.post, response.context.get('page_obj')[0])

    def test_group_page_correct_context(self):
        """Проверка контекста: group_list сформирован
        с правильным контекстом, пост на странице группы
        выводится с изображением"""
        response = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            )
        )
        self.check_post_context(self.post, response.context.get('page_obj')[0])

    def test_profile_page_correct_context(self):
        """Проверка контекста: profile сформирован с
        правильным контекстом, включена проверка вывода изображения."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.post.author}
            )
        )
        self.check_post_context(self.post, response.context.get('page_obj')[0])

    def test_post_detail_correct_context(self):
        """Проверка контекста: detail выводит один пост
        отфильтрованный по id, включена проверка вывода изображения."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.id}
            )
        )
        self.check_post_context(self.post, response.context.get('post'))

    def test_pages_uses_correct_template(self):
        """Проверка namespace:name в view правильные html-шаблоны"""
        templates_pages_names = {
            reverse('posts:home'): 'posts/index.html',
            reverse(
                'posts:group_posts',
                kwargs={'slug': f'{self.group.slug}'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': f'{self.user.username}'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{self.post.id}'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{self.post.id}'}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_group_page_correct_group(self):
        """group_list выводит записи только одной группы"""
        Post.objects.create(
            author=self.user,
            text='Пост без группы ',
        )
        group_another = Group.objects.create(
            title='Еще одна группа',
            slug='test_slug_another',
            description='Еще одна группа',
        )
        Post.objects.create(
            author=self.user,
            group=group_another,
            text='Пост с другой группа',
        )
        count_post_test_group = Post.objects.filter(group=self.group).count()

        group_page = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            )
        )
        self.assertEqual(
            len(group_page.context['page_obj']), count_post_test_group
        )

    def test_create_page_correct_context(self):
        """Проверка контекста: create сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_create'
            )
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_edit_page_correct_context(self):
        """Проверка контекста: edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.id}
            )
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    # def test_post_detail_correct_context(self):
    #     """Проверка контекста: detail выводит один пост
    #     отфильтрованный по id, включена проверка вывода изображения."""
    #     detail_post = self.authorized_client.get(
    #         reverse(
    #             'posts:post_detail',
    #             kwargs={'post_id': self.post.id}
    #         )
    #     )
    #     responses = {
    #         detail_post.context.get('post').author.username:
    #         self.post.author.username,
    #         detail_post.context.get('post').text:
    #         self.post.text,
    #         detail_post.context.get('post').group.title:
    #         self.post.group.title,
    #         detail_post.context.get('post').image:
    #         self.post.image,
    #     }
    #     for response, chek_value in responses.items():
    #         with self.subTest(response=response):
    #             self.assertEqual(response, chek_value)

    def test_follow_user(self):
        """Авторизованный пользователь может создвать подписки"""
        another_user = User.objects.create_user(username='another_user')
        Post.objects.create(
            author=another_user,
            text='Еще один тестовый пост'
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': another_user}
            )
        )
        self.assertTrue(Follow.objects.filter(
            user=self.user.id,
            author=another_user.id).exists()
        )

    def test_unfollow_user(self):
        """Авторизованный пользователь может удалять подписки"""
        another_user = User.objects.create_user(username='another_user')
        Post.objects.create(
            author=another_user,
            text='Еще один тестовый пост'
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': another_user}
            )
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': another_user}
            )
        )
        self.assertFalse(Follow.objects.filter(
            user=self.user.id,
            author=another_user.id).exists()
        )

    def test_follow_in_user_feed(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
        подписан ."""
        another_user = User.objects.create_user(username='another_user')
        new_post = Post.objects.create(
            author=another_user,
            text='Еще один тестовый пост'
        )

        # user подписан на another_use
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': another_user.username}
            )
        )
        # user видит пост another_user в своей ленте
        response_user = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(new_post, response_user.context['page_obj'])

    def test_notfollow_not_in_user_feed(self):
        """Новая запись пользователя не появляется в ленте тех, кто на него
        не подписан."""
        another_user = User.objects.create_user(username='another_user')
        new_post = Post.objects.create(
            author=another_user,
            text='Еще один тестовый пост'
        )
        response_user = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(new_post,
                         response_user.context['page_obj']
                         )


class ViewsPaginatorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_user')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.author)
        cls.group = Group.objects.create(
            title='test_group',
            slug='test-slug',
            description='test_description'
        )
        posts = [
            Post(
                author=cls.author,
                text=f'Тестовый пост {i}',
                group=cls.group
            ) for i in range(1, 14)
        ]
        Post.objects.bulk_create(posts)

        cls.templates = [
            reverse('posts:home'),
            reverse('posts:group_posts', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={
                'username': cls.author.username}
            )
        ]

    def page_contains_ten_records(self):
        """Проверка: количество постов на первой cтранице равно 10."""
        for template in len(self.templates):
            with self.subTest(template=template):
                response = self.client.get(self.templates[template])
                self.assertEqual(len(response.context['page_obj']), 10)

    def page_contains_three_records(self):
        """Проверка: количество постов на второй cтранице равно 3."""
        for template in len(self.templates):
            with self.subTest(template=template):
                response = self.client.get(
                    self.templates[template] + '?page=2'
                )
                self.assertEqual(len(response.context['page_obj']), 3)


class CacheViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(
            username='test user'
        )

    def test_home_page_cache(self):
        """Проверка: шаблон home правильно работет cache """
        post_new = Post.objects.create(
            text='Добавлен пост',
            author=self.user
        )
        response = self.client.get(reverse('posts:home'))
        created_object = response.context.get('page_obj')[0]
        self.assertEqual(created_object.text, post_new.text)

        post_new.delete()
        response_cached = self.client.get(reverse('posts:home'))
        self.assertEqual(response.content, response_cached.content)

        cache.clear()
        response_cleared = self.client.get(reverse('posts:home'))
        self.assertNotEqual(response_cached.content, response_cleared.content)
