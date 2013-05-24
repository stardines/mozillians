from django.contrib.auth.models import User
from django.test.utils import override_settings

from funfactory.urlresolvers import reverse
from mock import patch
from nose.tools import eq_, nottest
from product_details import product_details
from pyquery import PyQuery as pq

from apps.common import browserid_mock
from apps.common.tests.init import ESTestCase, user
from apps.groups.models import Group

from ..helpers import calculate_username, validate_username
from ..models import UserProfile, UsernameBlacklist


Group.objects.get_or_create(name='staff', system=True)
COUNTRIES = product_details.get_regions('en-US')


class RegistrationTest(ESTestCase):
    """Tests registration."""
    # Assertion doesn't matter since we monkey patched it for testing
    fake_assertion = 'mrfusionsomereallylongstring'

    def test_validate_username(self):
        """Test validate_username helper."""
        valid_usernames = ['giorgos', 'aakash',
                           'nikos', 'bat-man']

        invalid_usernames = ['administrator', 'test',
                             'no-reply', 'noreply', 'spam']

        for name in valid_usernames:
            self.assertTrue(validate_username(name),
                            'Username: %s did not pass test' % name)

        for name in invalid_usernames:
            self.assertFalse(validate_username(name),
                            'Username: %s did not pass test' % name)

    def test_mozillacom_registration(self):
        """Verify @mozilla.com users are auto-vouched and marked "staff"."""

        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid('mrfusion@mozilla.com'):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(username='ad',
                 email='mrfusion@mozilla.com',
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid('mrfusion@mozilla.com'):
            r = self.client.post(reverse('register'), d, follow=True)

        doc = pq(r.content)

        assert r.context['user'].get_profile().is_vouched, (
                "Moz.com should be auto-vouched")

        assert not doc('#pending-approval'), (
                'Moz.com profile page should not having pending vouch div.')

        assert r.context['user'].get_profile().groups.filter(name='staff'), (
                'Moz.com should belong to the "staff" group.')

    def test_plus_signs(self):
        email = 'mrfusion+dotcom@mozilla.com'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(username='ad',
                 email=email,
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('register'), d, follow=True)

        assert User.objects.filter(email=d['email'])

    def test_username(self):
        """Test that we can submit a perfectly cromulent username.

        We verify that /:username then works as well.

        """
        email = 'mrfusion+dotcom@mozilla.com'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)
        d = dict(email=email,
                 username='mrfusion',
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, "Problems if we didn't redirect...")
        u = User.objects.filter(email=d['email'])[0]
        eq_(u.username, 'mrfusion', "Username didn't get set.")

        r = self.mozillian_client.get(reverse('profile', args=['mrfusion']),
                                              follow=True)
        eq_(r.status_code, 200)
        eq_(r.context['profile'].user_id, u.id)

    def test_username_characters(self):
        """Verify usernames can have digits/symbols, but nothing too
        insane.

        """
        email = 'mrfusion+dotcom@mozilla.com'
        username = 'mr.fu+s_i-on@246'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(email=email,
                 username=username,
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, (
                'Registration flow should finish with a redirect.'))
        u = User.objects.get(email=d['email'])
        eq_(u.username, username, 'Username should be set to "%s".' % username)

        r = self.mozillian_client.get(reverse('profile', args=[username]),
                                              follow=True)
        eq_(r.status_code, 200)
        eq_(r.context['profile'].user_id, u.id)

        # Now test a username with even weirder characters that we don't allow.
        bad_user_email = 'mrfusion+coolbeans@mozilla.com'
        bad_username = 'mr.we*rd'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(email=bad_user_email,
                 username=bad_username,
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, (
                'Registration flow should fail; username is bad.'))
        assert not User.objects.filter(email=d['email']), (
                "User shouldn't exist; username was bad.")

    def test_bad_username(self):
        """'about' is a terrible username, as are its silly friends.

        Let's make some stop words *and* analyze the routing system,
        whenever someone sets their username and verify that they can't
        be 'about' or 'help' or anything that is in use.
        """
        email = 'mrfusion+dotcom@mozilla.com'
        badnames = UsernameBlacklist.objects.all().values_list('value',
                                                               flat=True)
        # BrowserID needs an assertion not to be whiney
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        for name in badnames:
            d = dict(email=email,
                     username=name,
                     full_name='Akaaaaaaash Desaaaaaaai',
                     optin=True)
            with browserid_mock.mock_browserid(email):
                r = self.client.post(reverse('register'), d)

            eq_(r.status_code, 200,
                'This form should fail for "%s", and say so.' % name)
            assert r.context['user_form'].errors, (
                "Didn't raise errors for %s" % name)

    def test_nickname_changes_before_vouch(self):
        """Notify pre-vouched users of URL change from nickname
        changes.

        See: https://bugzilla.mozilla.org/show_bug.cgi?id=736556

        """
        data = self.data_privacy_fields.copy()
        data.update({'username': 'foobar', 'full_name': 'Tofu Matt'})
        response = self.pending_client.post(reverse('profile.edit'),
                                            data, follow=True)
        assert 'You changed your username;' in response.content

    def test_repeat_username(self):
        """Verify one cannot repeat email adresses."""
        register = dict(username='repeatedun',
                        full_name='Akaaaaaaash Desaaaaaaai',
                        optin=True)

        # Create first user
        email1 = 'mRfUsIoN@mozilla.com'
        register.update(email=email1)
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email1):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with browserid_mock.mock_browserid(email1):
            self.client.post(reverse('register'), register, follow=True)

        self.client.logout()
        # Create a different user
        email2 = 'coldfusion@gmail.com'
        register.update(email=email2)
        with browserid_mock.mock_browserid(email2):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with browserid_mock.mock_browserid(email2):
            r = self.client.post(reverse('register'), register, follow=True)

        # Make sure we can't use the same username twice
        assert r.context['user_form'].errors, "Form should throw errors."

    def test_calculate_username(self):
        """Test calculated username."""
        eq_(calculate_username('nikoskoukos@example.com'), 'nikoskoukos')
        eq_(calculate_username('pending@example.com'), 'pending1')


class TestThingsForPeople(ESTestCase):
    """Verify that the wrong users don't see things."""

    @nottest
    def test_searchbox(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=text]')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=text]')
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('input[type=text]')

    def test_invitelink(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('a#invite')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('a#invite'), "Unvouched can't invite."
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('a#invite')

    def test_register_redirects_for_authenticated_users(self):
        """Ensure only anonymous users can register an account."""
        r = self.client.get(reverse('home'))
        self.assertTrue(200 == r.status_code,
                        'Anonymous users can access the homepage to '
                        'begin registration flow')

        r = self.mozillian_client.get(reverse('register'))
        eq_(302, r.status_code,
            'Authenticated users are redirected from registration.')

    def test_vouchlink(self):
        """No vouch link when PENDING looks at PENDING."""
        url = reverse('profile', args=['pending'])
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('#vouch-form button')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        errmsg = 'Self vouching... silliness.'
        assert not doc('#vouch-form button'), errmsg
        assert 'Vouch for me' not in r.content, errmsg

    @patch('users.admin.index_all_profiles')
    def test_es_index_admin_view(self, mock_obj):
        """Test that admin:user_index_profiles work fires a re-index."""
        self.mozillian.is_superuser = True
        self.mozillian.is_staff = True
        self.mozillian.save()
        url = reverse('admin:users_index_profiles')
        self.client.login(email=self.mozillian.email)
        self.client.get(url)
        mock_obj.assert_any_call()


class VouchTest(ESTestCase):

    def test_vouch_method(self):
        """Test UserProfile.vouch()

        Assert that a previously unvouched user shows up as unvouched
        in the database.

        Assert that when vouched they are listed as vouched.
        """
        vouchee = self.mozillian.get_profile()
        profile = self.pending.get_profile()
        assert not profile.is_vouched, 'User should not yet be vouched.'
        r = self.mozillian_client.get(reverse('search'),
                                      {'q': self.pending.email})
        assert profile.full_name not in r.content, (
                'User should not appear as a Mozillian in search.')

        profile.vouch(vouchee)
        profile = UserProfile.objects.get(pk=profile.pk)
        assert profile.is_vouched, 'User should be marked as vouched.'
        assert profile.date_vouched

        r = self.mozillian_client.get(reverse('profile', args=['pending']))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        assert 'Mozillian Profile' in r.content, (
                'User should appear as having a vouched profile.')
        assert not 'Pending Profile' in r.content, (
                'User should not appear as having a pending profile.')
        assert not doc('#pending-approval'), (
                'Pending profile div should not be in DOM.')

        # Make sure the user appears vouched in search results
        r = self.mozillian_client.get(reverse('search'),
                                      {'q': self.pending.email}, follow=True)
        assert str(profile.full_name) in r.content, (
                'User should appear as a Mozillian in search.')


class TestUser(ESTestCase):
    """Test User functionality."""

    def test_userprofile(self):
        u = user()

        UserProfile.objects.all().delete()

        # Somehow the User lacks a UserProfile
        # Note that u.get_profile() caches in memory.
        self.assertRaises(UserProfile.DoesNotExist,
                          lambda: u.userprofile)

        # Sign in
        with browserid_mock.mock_browserid(u.email):
            d = dict(assertion='qwer')
            self.client.post(reverse('browserid_verify'), d, follow=True)

        # Good to go
        assert u.get_profile()

    def test_blank_ircname(self):
        username = 'thisisatest'
        email = 'test@example.com'
        register = dict(username=username,
                        full_name='David Teststhings',
                        optin=True)
        d = {'assertion': 'rarrr'}

        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)
            self.client.post(reverse('register'), register, follow=True)

        u = User.objects.filter(email=email)[0]
        p = u.get_profile()
        p.ircname = ''
        eq_(p.ircname, '', 'We need to allow IRCname to be blank')


class TestMigrateRegistration(ESTestCase):
        """Test funky behavior of flee ldap."""
        email = 'robot1337@domain.com'

        def test_login(self):
            """Given an invite_url go to it and redeem an invite."""
            # Lettuce make sure we have a clean slate

            info = dict(full_name='Akaaaaaaash Desaaaaaaai', optin=True)
            self.client.logout()
            u = User.objects.create(username='robot1337', email=self.email)
            p = u.get_profile()

            p.full_name = info['full_name']
            u.save()
            p.save()

            # BrowserID needs an assertion not to be whiney
            d = dict(assertion='tofu')
            with browserid_mock.mock_browserid(self.email):
                r = self.client.post(reverse('browserid_verify'),
                                     d, follow=True)

            eq_(r.status_code, 200)

            # Now let's register
            with browserid_mock.mock_browserid(self.email):
                r = self.client.post(reverse('register'), info, follow=True)

            eq_(r.status_code, 200)


@override_settings(AUTO_VOUCH_DOMAINS=['mozilla.com'])
class AutoVouchTests(ESTestCase):

    def test_only_autovouch_in_staff(self):
        """Restrict the staff group to emails in AUTO_VOUCH_DOMAINS."""
        staff = Group.objects.get_or_create(name='staff', system=True)[0]
        staff_user = user(email='abcd@mozilla.com')
        staff_profile = staff_user.get_profile()
        staff_profile.save()
        assert staff in staff_profile.groups.all(), (
            'Auto-vouched email in staff group by default.')

        staff_profile.groups.remove(staff)
        staff_profile.save()
        assert staff in staff_profile.groups.all(), (
            'Auto-vouched email cannot be removed from staff group.')

        community_user = user()
        community_profile = community_user.get_profile()
        community_profile.save()
        assert staff not in community_profile.groups.all(), (
            'Non-auto-vouched email not automatically in staff group.')

        community_profile.groups.add(staff)
        community_profile.save()
        assert staff not in community_profile.groups.all(), (
            'Non-auto-vouched email cannot be added to staff group.')

    def test_autovouch_email(self):
        """Users with emails in AUTO_VOUCH_DOMAINS should be vouched."""
        auto_user = user(email='abcd@mozilla.com')
        auto_profile = auto_user.get_profile()
        auto_profile.save()
        assert auto_profile.is_vouched, 'Profile should be vouched.'
        assert auto_profile.vouched_by is None, (
            'Profile should not have a voucher.')

        non_auto_user = user()
        non_auto_profile = non_auto_user.get_profile()
        non_auto_profile.save()
        assert not non_auto_profile.is_vouched, (
            'Profile should not be vouched.')


class UsernameRedirectionMiddlewareTests(ESTestCase):
    # Assertion doesn't matter since we monkey patched it for testing
    def test_username_redirection_middleware(self):
        """Test the username redirection middleware."""
        response = self.mozillian_client.get('/%s' % self.mozillian.username,
                                             follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')

        response = self.client.get('/%s' % 'invaliduser', follow=True)
        self.assertTemplateUsed(response, '404.html')


class SearchTests(ESTestCase):

    def setUp(self):
        self.data = {'country': 'us',
                     'region': 'California',
                     'city': 'Mountain View',
                     'ircname': 'hax0r',
                     'bio': 'I love ice cream. I code. I tweet.',
                     'full_name': 'Nikos Koukos'}
        self.auto_user = user()
        self.up = self.auto_user.userprofile
        for key, value in self.data.iteritems():
            setattr(self.up, key, value)
        self.up.is_vouched = True
        self.up.save()

    def test_search_generic(self):
        for key, value in self.data.iteritems():
            if key == 'country':
                value = COUNTRIES[value]
            results = UserProfile.search(value)
            self.assertEqual(len(results), 1)

        results = UserProfile.search(self.up.full_name)
        self.assertEqual(len(results), 1)

        results = UserProfile.search(self.up.full_name[:2])
        self.assertEqual(len(results), 1)

        results = UserProfile.search(
            self.up.bio.split(' ')[3])
        self.assertEqual(len(results), 1)

class UserProfileManagerTests(ESTestCase):

    def test_complete_query(self):
        """Test complete() of UserProfileManager."""
        eq_(UserProfile.objects.complete().count(), 3)

    def test_public_indexable_query(self):
        """Test public_indexable() of UserProfileManager."""
        eq_(UserProfile.objects.public_indexable().count(), 2)

    def test_not_public_indexable_query(self):
        """Test not_public_indexable() of UserProfileManager."""
        eq_(UserProfile.objects.not_public_indexable().count(), 1)
