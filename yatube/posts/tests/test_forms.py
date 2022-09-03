import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post, User

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
            description='Тестовое описание',
            title='Тестовая группа',
            slug='test-slug',
        )
        cls.post_for_test = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.post_author = Client()
        cls.post_author.force_login(cls.post_for_test.author)
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
        group_field = self.group.id
        form_data = {
            'image': self.upload,
            'group': group_field,
            'text': 'Тест создание поста',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data
        )
        self.assertEqual(Post.objects.count(), count + 1)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user}
        ))
        self.assertTrue(
            Post.objects.filter(
                author=self.user,
                group=self.group.id,
                text=form_data['text'],
            ).exists()
        )
        response_for_image = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.user}))
        self.assertIn(
            self.upload.name,
            response_for_image.context.get('page_obj')[0].image.name
        )

    def test_edit_post(self):
        """Проверка редактирования поста"""
        group_field = self.group.id
        form_data = {
                    'text': 'Обновленный текст',
                    'group': group_field
        }
        self.post_author.post(reverse(
            'posts:post_edit', kwargs={'post_id': self.post_for_test.id}
        ),
            data=form_data,
            follow=True
        )
        self.assertTrue(
            Post.objects.filter(
                id=self.post_for_test.id,
                group=self.group.id,
                text=form_data['text'],
            ).exists()
        )
        response_edit_post = self.post_author.get(reverse(
            'posts:post_detail', kwargs={'post_id': f'{self.post_for_test.id}'}
        ))
        self.assertEqual(response_edit_post.context.get(
            'post').author.username, self.post_for_test.author.username
        )
        self.assertEqual(response_edit_post.context.get(
            'post').text, form_data['text']
        )

    def test_comment_create(self):
        """Проверка создание комментария авторизованным пользователем,
        комментарий создан и появился на странице поста"""
        count = self.post_for_test.comments.count()
        form_data = {'text': 'Текст созданного комментария', }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post_for_test.id}),
            data=form_data,
            follow=True
        )
        self.assertTrue(
            Comment.objects.filter(
                post=self.post_for_test.id,
                text=form_data['text']).exists()
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post_for_test.id}
        ))
        self.assertEqual(self.post_for_test.comments.count(), count + 1)
        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post_for_test.id})
        )
        self.assertEqual(
            response.context.get('comments')[0].text, form_data['text']
        )

    def test_anonymous_cant_comment(self):
        """Комменарий не может быть внесен неавторизованным пользователем"""
        count = Comment.objects.filter(post=self.post_for_test.id).count()
        form_data = {
            'text': 'Текст попытка неавтиоризованного пользователя',
        }
        self.client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post_for_test.id}),
            data=form_data,
            follow=True
        )
        self.assertFalse(
            Comment.objects.filter(
                post=self.post_for_test.id,
                text=form_data['text']
            ).exists()
        )
        self.assertEqual(
            Comment.objects.filter(post=self.post_for_test.id).count(), count
        )
