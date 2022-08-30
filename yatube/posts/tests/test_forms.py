import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
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
        cls.post1 = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post_author = Client()
        cls.post_author.force_login(cls.post1.author)
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.upload = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Проверка создания поста, включена проверка вывода изображения."""
        count = Post.objects.count()
        form_data = {
            'text': 'Тест создание поста',
            'image': self.upload,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        self.assertEqual(Post.objects.count(), count + 1)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user}
        ))
        response_for_image = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user}))
        self.assertIn(self.upload.name,
                      response_for_image.context.get('page_obj')[0].image.name)

    def test_edit_post(self):
        """Проверка редактирования поста"""
        form_data = {'text': 'Обновленный текст'}
        self.post_author.post(reverse(
            'posts:post_edit', kwargs={'post_id': self.post1.pk}
        ),
            data=form_data,
            follow=True
        )
        self.assertTrue(
            Post.objects.filter(
                id=self.post1.pk,
                text=form_data['text'],
            ).exists()
        )

    def test_comment_create(self):
        """Проверка создание комментария авторизованным пользователем,
        комментарий создан и появился на странице поста"""
        count = Comment.objects.filter(post=self.post1.id).count()
        form_data = {'text': 'Текст созданного комментария', }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment', kwargs={'post_id': self.post1.id}),
            data=form_data,
            follow=True
        )
        self.assertTrue(
            Comment.objects.filter(
               post=self.post1.id,
               text=form_data['text']).exists()
        )
        self.assertRedirects(response, reverse(
           'posts:post_detail', kwargs={'post_id': self.post1.id}
        ))
        self.assertEqual(
            Comment.objects.filter(post=self.post1.id).count(), count + 1
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post1.id})
        )
        self.assertEqual(
            response.context.get('comments')[0].text, form_data['text']
        )

    def test_comment_not_create_no_authorized_user(self):
        """Комменарий не может быть внесен неавторизованным пользователем"""
        count = Comment.objects.filter(post=self.post1.id).count()
        form_data = {
           'text': 'Текст попытка неавтиоризованного пользователя',
        }
        self.client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post1.id}),
            data=form_data,
            follow=True
        )
        self.assertFalse(
            Comment.objects.filter(
                post=self.post1.id,
                text=form_data['text']).exists()
        )
        self.assertEqual(
            Comment.objects.filter(post=self.post1.id).count(), count
        )
