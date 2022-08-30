import shutil
import tempfile
from time import sleep

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(
            username='test_user_1'
        )
        cls.group_1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test_1-slug',
            description='Тестовое описание 1',
        )
        cls.post_1 = Post.objects.create(
            author=cls.user_1,
            text='Тестовый пост 1',
            group=cls.group_1
        )
        sleep(0.5)
        cls.user_2 = User.objects.create_user(
            username='test_user_2'
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test_2-slug',
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
        cls.post_2 = Post.objects.create(
            author=cls.user_2,
            text='Тестовый пост 2',
            image=cls.uploaded,
            group=cls.group_2
        )
        cls.authorized_client = Client()
        # Авторизуем пользователя
        cls.authorized_client.force_login(cls.user_1)
        # Создаем клиента автора
        cls.post_author = Client()
        # Создаем пользователя автора
        cls.post_author.force_login(cls.post_1.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """Проверка namespace:name в view правильные html-шаблоны"""
        templates_pages_names = {
            reverse('posts:home'): 'posts/index.html',
            reverse(
                'posts:group_posts', kwargs={'slug': f'{self.group_1.slug}'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': f'{self.user_1.username}'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': f'{self.post_1.id}'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': f'{self.post_1.id}'}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.post_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Проверка контекста: home сформирован с правильным контекстом,
        включена проверка вывода изображения."""
        response = self.authorized_client.get(reverse('posts:home'))
        # Cодержание первого элемента совпадает с ожидаемым
        # ('page_obj')[0] второй пост т.к сортировка по дате публикации.
        first_object = response.context.get('page_obj')[0]

        post_author = first_object.author.username
        post_text = first_object.text
        post_group = first_object.group.title
        post_image = first_object.image
        count = len(response.context['page_obj'])

        self.assertEqual(post_author, self.post_2.author.username)
        self.assertEqual(post_text, self.post_2.text)
        self.assertEqual(post_group, self.post_2.group.title)
        self.assertEqual(post_image, self.post_2.image)
        self.assertEqual(count, 2)

    def test_group_page_correct_context(self):
        """Проверка контекста: group_list сформирован
        с правильным контекстом, включена проверка вывода
        изображения."""
        response = self.authorized_client.get(reverse(
            'posts:group_posts', kwargs={'slug': self.group_2.slug}
        ))
        first_object = response.context.get('page_obj')[0]
        post_group = first_object.group.title
        post_image = first_object.image
        count = len(response.context['page_obj'])
        self.assertEqual(post_group, self.post_2.group.title)
        self.assertEqual(post_image, self.post_2.image)
        self.assertEqual(count, 1)

    def test_profile_page_correct_context(self):
        """Проверка контекста: profile сформирован с
        правильным контекстом, включена проверка вывода изображения."""
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.post_2.author}
        ))
        first_object = response.context.get('page_obj')[0]
        post_author = first_object.author.username
        post_image = first_object.image
        count = len(response.context['page_obj'])
        self.assertEqual(post_author, self.post_2.author.username)
        self.assertEqual(post_image, self.post_2.image)
        self.assertEqual(count, 1)

    def test_create_page_correct_context(self):
        """Проверка контекста: create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_create'
        ))
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
        response = self.post_author.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post_1.id}
        ))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_detail_correct_context(self):
        """Проверка контекста: detail выводит один пост
        отфильтрованный по id, включена проверка вывода изображения."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post_2.id}
        ))
        self.assertEqual(response.context.get(
            'post').author.username, self.post_2.author.username
        )
        self.assertEqual(response.context.get(
            'post').text, self.post_2.text
        )
        self.assertEqual(response.context.get(
            'post').group.title, self.post_2.group.title
        )
        self.assertEqual(response.context.get(
            'post').image, self.post_2.image
        )

    def test_follow_authorised_user(self):
        """Авторизованный пользователь может создвать и удалять подписки"""
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2.username}
        ))
        self.assertTrue(Follow.objects.filter(
            user=self.user_1.id,
            author=self.user_2.id).exists()
        )
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_2.username}
        ))
        self.assertFalse(Follow.objects.filter(
            user=self.user_1.id,
            author=self.user_2.id).exists()
        )

    def test_follow_output_in_user_feed(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
        подписан и не появляется в ленте тех, кто не подписан."""
        authorized_client2 = Client()
        authorized_client2.force_login(self.user_2)

        new_post = Post.objects.create(
            text='Новый пост test user 2',
            author=self.user_2
        )
        # user_1 подписан на user_2
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_2.username}
        ))
        # user_1 видит пост user_2 в своей ленте
        # user_2 не видит пост user_1 в своей ленте
        response_user_1 = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        response_user_2 = authorized_client2.get(reverse('posts:follow_index'))
        self.assertIn(new_post, response_user_1.context['page_obj'])
        self.assertNotIn(self.post_1, response_user_2.context['page_obj'])


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
        for i in range(13):
            cls.post = Post.objects.create(
                text=f'test_post{i}',
                group=cls.group,
                author=cls.author
            )

    def test_first_home_page_contains_ten_records(self):
        """Проверка: количество постов на первой home странице равно 10."""
        response = self.client.get(reverse('posts:home'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_home_page_contains_three_records(self):
        """Проверка: на второй home странице должно быть три поста."""
        response = self.client.get(reverse('posts:home') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_group_page_contains_ten_records(self):
        """Проверка: количество постов на первой group странице равно 10."""
        response = self.client.get(reverse(
            'posts:group_posts', kwargs={'slug': self.group.slug}
        ))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_group_page_contains_three_records(self):
        """Проверка: на второй group странице должно быть три поста."""
        response = self.client.get(reverse(
            'posts:group_posts',
            kwargs={'slug': self.group.slug}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_profile_page_contains_ten_records(self):
        """Проверка: количество постов на первой profile странице равно 10."""
        response = self.client.get(reverse(
            'posts:profile', kwargs={'username': self.author.username}
        ))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_profile_page_contains_three_records(self):
        """Проверка: на второй profile странице должно быть три поста."""
        response = self.client.get(reverse(
            'posts:group_posts',
            kwargs={'slug': self.group.slug}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)


class CacheViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_1 = User.objects.create_user(
            username='test_user_1'
        )
        cls.group_1 = Group.objects.create(
            title='Тестовая группа 1',
            slug='test_1-slug',
            description='Тестовое описание 1',
        )
        cls.post_1 = Post.objects.create(
            author=cls.user_1,
            text='Тестовый пост 1',
            group=cls.group_1
        )
        cls.guest_client = Client()

    def test_home_page_cache(self):
        """Проверка: шаблон home правильно работет cache """
        self.post_new = Post.objects.create(
            text='Добавлен пост',
            author=self.user_1
        )
        response = self.guest_client.get(reverse('posts:home'))
        created_object = response.context.get('page_obj')[0]
        count = len(response.context['page_obj'])
        self.assertEqual(created_object.text, self.post_new.text)
        self.assertEqual(count, 2)

        Post.objects.filter(id=self.post_new.id).delete()
        created_object = response.context.get('page_obj')[0]
        response_cached = self.guest_client.get(reverse('posts:home'))
        self.assertEqual(response.content, response_cached.content)

        cache.clear()
        response_cleared = self.guest_client.get(reverse('posts:home'))
        self.assertNotEqual(response_cached.content, response_cleared.content)
