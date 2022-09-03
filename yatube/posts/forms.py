from django import forms

from .models import Comment, Post


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {'text': 'Текст комментария'}
        help_texts = {'text': 'Напишите свой комментарий здесь'}


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'image': 'Картинка',
            'group': 'Группа',
            'text': 'Текст поста'
        }
        help_texts = {
            'image': 'Загрузите изображение',
            'group': 'Выберите нужную группу из списка',
            'text': 'Напишите свой пост здесь'
        }
