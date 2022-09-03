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
        cls.user_first_added = User.objects.create_user(
            username='test_first_added'
        )
        cls.group_first = Group.objects.create(
            title='Тестовая группа для первого поста',
            slug='test_first_added-slug',
            description='Тестовое описание первого поста',
        )
        cls.post_first_added = Post.objects.create(
            author=cls.user_first_added,
            text='Тестовый первый добавленный пост',
            group=cls.group_first
        )
        cls.user_second_added = User.objects.create_user(
            username='test_user_second_added'
        )
        cls.group_second_added = Group.objects.create(
            title='Тестовая группа для второго поста',
            slug='test_second_added-slug',
            description='Тестовое описание второго поста',
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
        cls.post_second_added = Post.objects.create(
            author=cls.user_second_added,
            text='Тестовый второй добавленный пост ',
            image=cls.uploaded,
            group=cls.group_second_added
        )
        cls.authorized_client = Client()
        # Авторизуем пользователя
        cls.authorized_client.force_login(cls.user_first_added)
        # Gользователь является авторром
        cls.authorized_client.force_login(cls.post_first_added.author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_pages_uses_correct_template(self):
        """Проверка namespace:name в view правильные html-шаблоны"""
        templates_pages_names = {
            reverse('posts:home'): 'posts/index.html',
            reverse(
                'posts:group_posts',
                kwargs={'slug': f'{self.group_first.slug}'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': f'{self.user_first_added.username}'}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{self.post_first_added.id}'}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': f'{self.post_first_added.id}'}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Проверка контекста: home сформирован с правильным контекстом,
        включена проверка вывода изображения."""
        response = self.authorized_client.get(reverse('posts:home'))
        # Cодержание первого элемента совпадает с ожидаемым
        # ('page_obj')[0] second_added пост т.к сортировка по дате публикации.
        first_object = response.context.get('page_obj')[0]
        self.assertEqual(len(response.context['page_obj']), 2)

        responses = {
            first_object.author.username:
            self.post_second_added.author.username,
            first_object.text:
            self.post_second_added.text,
            first_object.group.title:
            self.post_second_added.group.title,
            first_object.image:
            self.post_second_added.image,
        }
        for response, chek_value in responses.items():
            with self.subTest(response=response):
                self.assertEqual(response, chek_value)

    def test_group_page_correct_context(self):
        """Проверка контекста: group_list сформирован
        с правильным контекстом, на страницу Все посты группы
        выводится пост с изображением"""
        response = self.authorized_client.get(reverse(
            'posts:group_posts',
            kwargs={'slug': self.group_second_added.slug}
            )
        )
        first_object = response.context.get('page_obj')[0]

        self.assertEqual(first_object.group.title,
                         self.post_second_added.group.title
                         )
        self.assertEqual(first_object.image, self.post_second_added.image)
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_profile_page_correct_context(self):
        """Проверка контекста: profile сформирован с
        правильным контекстом, включена проверка вывода изображения."""
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.post_second_added.author}
            )
        )
        first_object = response.context.get('page_obj')[0]

        self.assertEqual(first_object.author.username,
                         self.post_second_added.author.username
                         )
        self.assertEqual(first_object.image, self.post_second_added.image)
        self.assertEqual(len(response.context['page_obj']), 1)

    def test_create_page_correct_context(self):
        """Проверка контекста: create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
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
        response = self.authorized_client.get(reverse(
            'posts:post_edit',
            kwargs={'post_id': self.post_first_added.id}
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

    def test_post_detail_correct_context(self):
        """Проверка контекста: detail выводит один пост
        отфильтрованный по id, включена проверка вывода изображения."""
        first_detail_post = self.authorized_client.get(reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post_second_added.id}
            )
        )
        responses = {
            first_detail_post.context.get('post').author.username:
            self.post_second_added.author.username,
            first_detail_post.context.get('post').text:
            self.post_second_added.text,
            first_detail_post.context.get('post').group.title:
            self.post_second_added.group.title,
            first_detail_post.context.get('post').image:
            self.post_second_added.image,
        }
        for response, chek_value in responses.items():
            with self.subTest(response=response):
                self.assertEqual(response, chek_value)

    def test_create_follow_authorised_user(self):
        """Авторизованный пользователь может создвать подписки"""
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_second_added.username}
        ))
        self.assertTrue(Follow.objects.filter(
            user=self.user_first_added.id,
            author=self.user_second_added.id).exists()
        )

    def test_delete_follow_authorised_user(self):
        """Авторизованный пользователь может удалять подписки"""
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.user_second_added.username}
        ))
        self.assertFalse(Follow.objects.filter(
            user=self.user_first_added.id,
            author=self.user_second_added.id).exists()
        )

    def test_follow_in_user_feed(self):
        """Новая запись пользователя появляется в ленте тех, кто на него
        подписан ."""
        authorized_new_client = Client()
        authorized_new_client.force_login(self.user_second_added)

        new_post = Post.objects.create(
            text='Новый пост second added user',
            author=self.user_second_added
        )
        # user_first_added подписан на user_second_added
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.user_second_added.username}
        ))
        # user_first_added видит пост user_second_added в своей ленте
        response_user_first_added = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(new_post, response_user_first_added.context['page_obj'])

    def test_notfollow_not_in_user_feed(self):
        """Новая запись пользователя не появляется в ленте тех, кто на него
        не подписан."""
        new_user = User.objects.create_user(
            username='test_new_user'
        )
        new_authorized_client = Client()
        new_authorized_client.force_login(new_user)
        new_post = Post.objects.create(
            text='Новый пост user_new',
            author=new_user
        )
        # user_first_added не подписан на new_user
        response_user_first_added = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        # user_first_added не видит записи new_user
        self.assertNotIn(new_post,
                         response_user_first_added.context['page_obj']
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

        cls.templates = {
                1: reverse('posts:home'),
                2: reverse('posts:group_posts',
                           kwargs={'slug': cls.group.slug}
                           ),
                3: reverse('posts:profile',
                           kwargs={'username': cls.author.username}
                           )
            }

    def page_contains_ten_records(self):
        """Проверка: количество постов на первой cтранице равно 10."""
        for i in self.templates.key():
            with self.subTest(i=i):
                response = self.client.get(self.templates[i])
                self.assertEqual(len(response.context['page_obj']), 10)

    def page_contains_three_records(self):
        """Проверка: количество постов на второй cтранице равно 3."""
        for i in self.templates.key():
            with self.subTest(i=i):
                response = self.client.get(self.templates[i] + '?page=2')
                self.assertEqual(len(response.context['page_obj']), 3)


class CacheViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_first_added = User.objects.create_user(
            username='test_user_first_added'
        )
        cls.group_first = Group.objects.create(
            title='Тестовая группа первого поста',
            slug='test_first_added-slug',
            description='Тестовое описание',
        )
        cls.post_first_added = Post.objects.create(
            author=cls.user_first_added,
            text='Тестовый пост первый добавленный',
            group=cls.group_first
        )
        cls.guest_client = Client()

    def test_home_page_cache(self):
        """Проверка: шаблон home правильно работет cache """
        post_count = Post.objects.count()
        self.post_new = Post.objects.create(
            text='Добавлен пост',
            author=self.user_first_added
        )
        response = self.guest_client.get(reverse('posts:home'))
        created_object = response.context.get('page_obj')[0]
        self.assertEqual(created_object.text, self.post_new.text)
        self.assertEqual(len(response.context['page_obj']), post_count + 1)

        self.post_new.delete()
        created_object = response.context.get('page_obj')[0]
        response_cached = self.guest_client.get(reverse('posts:home'))
        self.assertEqual(response.content, response_cached.content)

        cache.clear()
        response_cleared = self.guest_client.get(reverse('posts:home'))
        self.assertNotEqual(response_cached.content, response_cleared.content)
