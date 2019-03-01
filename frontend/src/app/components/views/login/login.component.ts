import { Component, Input, OnInit, OnChanges } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { NgForm } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';

import { ApiService, MetadataPayload, Metadata } from '../../../services/api.service';
import { CookieService } from '../../../services/cookie.service';


// avoiding having password persisted in javascript
class LoginForm {
  username?: string;
  rememberMe?: boolean;
}

@Component({
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.scss'],
    selector: 'app-login'
})
export class LoginComponent implements OnInit, OnChanges {

  public message: string;
  public warnMessage: string;
  public metadata: Metadata;
  form: LoginForm = { rememberMe: false };
  redirectUrl = '/feedback';
  submitting = false;
  isDisconnected = false;

  constructor(public api: ApiService, private cookie: CookieService, private router: Router, private route: ActivatedRoute) {}

  ngOnInit() {
    const username = this.cookie.getCookie('username');
    if (username) {
      this.form.rememberMe = true;
      this.form.username = username;
    }
    if (this.route.snapshot.queryParams.logoutSuccess) {
      this.message = 'You have successfully logged out.';
    }
    if (this.route.snapshot.queryParams.from) {
      this.redirectUrl = this.route.snapshot.queryParams.from;
    }
    this.api.getMetadata().subscribe(
      (result: MetadataPayload) => {
        this.metadata = result.metadata;
        if (result.metadata.passwordlessAccess) {
          this.warnMessage = 'UNSAFE PASSWORDLESS ACCESS IS ENABLED ON WEB SERVER. THIS SHOULD NOT BE ON IN PRODUCTION!';
        }
      },
      () => {
        this.isDisconnected = true;
      }
    );
  }

  ngOnChanges() {
    if (this.form.rememberMe) {
      this.cookie.setCookie('username', this.form.username);
    }
  }

  onRememberMeToggle(value: boolean) {
    this.form.rememberMe = value;
    if (value) {
      this.cookie.setCookie('username', this.form.username);
    } else {
      this.cookie.deleteCookie('username');
    }
  }

  private setErrorMessage(error: HttpErrorResponse) {
    switch (error.status) {
      case 401:
        this.message = `Incorrect username and/or password. Please email ${this.metadata.supportEmail} if you have anymore issues`;
        break;
      case 404:
        this.message = `User with Windows username "${this.form.username}" not found. If you think this
           should not be the case, please email ${this.metadata.supportEmail} to synchronise User models with LDAP.`;
        break;
      case 500:
        this.message = `Backend service unable to serve the request. Please email ${this.metadata.supportEmail}.`;
        break;
      default:
        this.message = `Unable to login. Please email ${this.metadata.supportEmail} if you have any more issues.`;
    }
  }

  onSubmit(loginForm: NgForm) {
    this.submitting = true;
    this.message = null;
    this.api.login(loginForm.value.username, loginForm.value.password).subscribe(
      _ => {
        this.router.navigate([this.redirectUrl]);
        if (this.form.rememberMe) {
          this.cookie.setCookie('username', this.form.username);
        }
        this.submitting = false;
      },
      err => {
        this.setErrorMessage(err);
        this.submitting = false;
      }
    );
  }
}
