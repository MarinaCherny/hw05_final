from django.contrib import admin

from .models import Group, Post


class GroupAdmin(admin.ModelAdmin):
    list_display = ('pk', 'title', 'slug', 'description')
    list_editable = ('description',)
    search_fields = ('title',)
    empty_value_display = '-пусто-'


class PostAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'pub_date', 'author', 'group')
    list_editable = ('group',)
    search_fields = ('text',)
    list_filter = ('pub_date',)
    empty_value_display = '-пусто-'


# Источником конфигурации при регистрации модели Post
# назначен класс PostAdmin
admin.site.register(Post, PostAdmin)
# Источником конфигурации при регистрации модели Group
# назначен класс GroupAdmin
admin.site.register(Group, GroupAdmin)
